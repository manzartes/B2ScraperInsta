import streamlit as st
import requests
import json
import google.generativeai as genai
import time
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="B2Scraper Insta", page_icon="⚡", layout="wide")

# ==========================================
# 🔑 CHAVES E CONFIGURAÇÕES INICIAIS
# ==========================================
try:
    CHAVE_SERPER_PADRAO = st.secrets.get("CHAVE_SERPER", "")
    CHAVE_GEMINI_PADRAO = st.secrets.get("CHAVE_GEMINI", "")
    URL_WEBHOOK_PLANILHA = st.secrets.get("WEBHOOK_PLANILHA", "")
except Exception:
    CHAVE_SERPER_PADRAO = ""
    CHAVE_GEMINI_PADRAO = ""
    URL_WEBHOOK_PLANILHA = ""

# --- INICIALIZANDO MEMÓRIAS E ESTADOS ---
if "historico_leads" not in st.session_state:
    st.session_state["historico_leads"] = []
if "leads_aprovados_tela" not in st.session_state:
    st.session_state["leads_aprovados_tela"] = []
if "leads_reprovados_tela" not in st.session_state:
    st.session_state["leads_reprovados_tela"] = []
if "blacklist_arrobas" not in st.session_state:
    st.session_state["blacklist_arrobas"] = set()
if "proxima_pagina" not in st.session_state:
    st.session_state["proxima_pagina"] = 1

# --- VALORES PADRÃO PARA CRITÉRIOS E MENSAGEM (DINÂMICOS) ---
if "prompt_criterios" not in st.session_state:
    st.session_state["prompt_criterios"] = """O seu ICP EXATO é: Dono de pequena/média empresa, Profissional liberal, Consultor/mentor, Médico/odontólogo, Advogado, Corretor/assessor, Gestor/comercial, Executivo, Engenheiro/arquiteto.

REGRAS DE REPROVAÇÃO:
1. Foto inadequada (ex: sem camisa, amadora demais).
2. Seguidores: Mais de 50k (queremos leads menores/médios).
3. Perfil Privado: REPROVAR IMEDIATAMENTE."""

if "prompt_script" not in st.session_state:
    st.session_state["prompt_script"] = """Olá, [PRONOME_E_NOME]. Tudo bem?
Espero que sim.

Aqui é o [SEU_NOME], muito prazer. Eu trabalho há mais de [ANOS_EXP] anos ajudando empresários a serem percebidos como autoridade e venderem mais.

Me deparei com seu perfil e gostei muito do conteúdo sobre [ÁREA X], principalmente seu foco em [ESPECIALIDADE].

Vi pontos que podem estar limitando seu faturamento. Posso compartilhar essas observações?"""

# Arrays de Memória da IA
if "bons_exemplos" not in st.session_state: st.session_state["bons_exemplos"] = []
if "maus_exemplos" not in st.session_state: st.session_state["maus_exemplos"] = []
if "feedbacks_dados" not in st.session_state: st.session_state["feedbacks_dados"] = [] 

# ==========================================
# ⚙️ MENU LATERAL (GAVETAS)
# ==========================================
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    
    with st.expander("🎯 Destino CRM", expanded=True):
        st.session_state["url_webhook"] = st.text_input("URL do Webhook:", type="password", value=st.session_state.get("url_webhook", URL_WEBHOOK_PLANILHA))
        st.session_state["nome_aba"] = st.text_input("Aba de Entrada (CRM):", value=st.session_state.get("nome_aba", "ABRIL/26"))

    with st.expander("🧠 Personalização da IA", expanded=False):
        st.markdown("### 1. Critérios de Qualificação")
        st.session_state["prompt_criterios"] = st.text_area("Defina o ICP e Regras:", value=st.session_state["prompt_criterios"], height=200)
        
        st.markdown("### 2. Modelo de Mensagem")
        st.session_state["prompt_script"] = st.text_area("Script Base (Use as tags):", value=st.session_state["prompt_script"], height=250, help="Tags disponíveis: [PRONOME_E_NOME], [ÁREA X], [ESPECIALIDADE]")

    with st.expander("👤 Seu Perfil & API", expanded=False):
        seu_nome = st.text_input("Seu Nome:", value="Henrique Durant")
        anos_exp = st.text_input("Anos de Experiência:", value="5")
        st.session_state["pronome_lead"] = st.text_input("Pronome Base Lead:", placeholder="Ex: Dr.")
        st.divider()
        st.session_state["api_key_serper"] = st.text_input("Serper API:", type="password", value=st.session_state.get("api_key_serper", CHAVE_SERPER_PADRAO))
        st.session_state["api_key_gemini"] = st.text_input("Gemini API:", type="password", value=st.session_state.get("api_key_gemini", CHAVE_GEMINI_PADRAO))

    with st.expander("🚫 Blacklist", expanded=False):
        st.session_state["aba_blacklist"] = st.text_input("Aba da Blacklist:", value=st.session_state.get("aba_blacklist", "BLACKLIST"))
        bl_manual_text = st.text_area("Adicionar @avulsos:", placeholder="@perfil1")
        blacklist_manual = {a.strip() for a in bl_manual_text.split("\n") if a.strip()}

# ==========================================
# 🛠️ FUNÇÕES DE APOIO (PLANILHA / BUSCA)
# ==========================================
def enviar_lead_para_planilha(lead_dados):
    webhook = st.session_state["url_webhook"]
    if not webhook: return False
    try:
        resposta = requests.post(webhook, json=lead_dados)
        return resposta.ok and "Sucesso" in resposta.text
    except: return False

def puxar_blacklist_automatica():
    webhook = st.session_state["url_webhook"]; aba = st.session_state.get("aba_blacklist", "BLACKLIST")
    if not webhook or not aba: return set()
    try:
        res = requests.get(f"{webhook}?aba={aba}")
        if res.ok:
            return {str(a).strip().replace("https://www.instagram.com/", "@").replace("/", "") for a in res.json().get("leads", []) if str(a).strip()}
    except: pass
    return set()

def garimpar_perfis_google(nicho, hashtag, local, negativos, frase, qtd, api_serper, pagina=1):
    url = "https://google.serper.dev/search"
    query = 'site:instagram.com -inurl:p -inurl:reel -inurl:explore -inurl:tags'
    if nicho: query += f' "{nicho}"'
    if hashtag: query += f' {hashtag if hashtag.startswith("#") else f"#{hashtag}"}'
    if local: query += f' "{local}"'
    if frase: query += f' intext:"{frase}"'
    if negativos:
        for n in [t.strip() for t in negativos.split(",") if t.strip()]: query += f' -{n}'
    
    encontrados = []
    ignorar = ['p', 'reel', 'reels', 'explore', 'tags', 'stories', 'tv', 'channel', 'about', 'legal', 'directory']
    bl_total = st.session_state["blacklist_arrobas"].union(blacklist_manual).union(puxar_blacklist_automatica())
    
    for p in range(pagina, pagina + 5):
        if len(encontrados) >= qtd: break
        payload = json.dumps({"q": query, "page": p, "num": 10})
        headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
        try:
            res = requests.post(url, headers=headers, data=payload)
            if not res.ok: break
            for item in res.json().get("organic", []):
                match = re.search(r'instagram\.com/([^/?]+)', item.get("link", ""))
                if match:
                    u = f"@{match.group(1).strip()}"
                    if match.group(1).lower() not in ignorar and u not in bl_total and u not in encontrados:
                        encontrados.append(u)
                        if len(encontrados) >= qtd: break
        except: break
        time.sleep(0.5)
    return encontrados[:qtd], p + 1

# ==========================================
# 🧠 CÉREBRO DA IA (GEMINI 2.5 FLASH)
# ==========================================
def analisar_e_gerar_script(arroba, bio, api_gemini, seu_nome, exp, pronome_base):
    try:
        genai.configure(api_key=api_gemini)
        modelo = genai.GenerativeModel('gemini-2.5-flash')
        
        # Puxa as configurações do menu lateral
        criterios_usuario = st.session_state["prompt_criterios"]
        script_usuario = st.session_state["prompt_script"]
        
        treinamento = ""
        if st.session_state["bons_exemplos"]:
            treinamento += f"\n🚨 EXEMPLOS APROVADOS:\n- " + "\n- ".join(st.session_state["bons_exemplos"][-3:])
        if st.session_state["maus_exemplos"]:
            treinamento += f"\n🚨 EXEMPLOS REPROVADOS:\n- " + "\n- ".join(st.session_state["maus_exemplos"][-3:])

        prompt = f"""
        Você é {seu_nome}, BDR especialista. Analise o lead abaixo.

        --- CRITÉRIOS DE AVALIAÇÃO (DEFINIDOS PELO USUÁRIO) ---
        {criterios_usuario}
        {treinamento}

        --- DADOS DO LEAD ({arroba}) ---
        Bio/Resumo: "{bio}"

        Sua tarefa:
        1. Avalie se é APROVADO ou REPROVADO conforme os critérios.
        2. Se aprovado, gere o script abaixo substituindo as tags:
        
        --- MODELO DE SCRIPT (DEFINIDO PELO USUÁRIO) ---
        {script_usuario}

        REGRAS PARA O SCRIPT:
        - [SEU_NOME] = {seu_nome}
        - [ANOS_EXP] = {exp}
        - [PRONOME_E_NOME]: Analise o gênero e use o pronome "{pronome_base}" flexionado (ex: Dra. se mulher) + primeiro nome. Se pronome vazio, use só o nome.
        - [ÁREA X] e [ESPECIALIDADE]: Extraia da bio do lead.
        - Mantenha parágrafos e use "\\n\\n" no JSON para quebras de linha.

        Retorne APENAS um JSON válido:
        {{
            "status": "APROVADO" ou "REPROVADO",
            "motivo": "justificativa curta",
            "script_1": "texto final da mensagem"
        }}
        """
        
        resposta = modelo.generate_content(prompt)
        texto_limpo = resposta.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)
    except Exception as e:
        return {"status": "ERRO", "motivo": str(e)}

# ==========================================
# 🖥️ COMPONENTES DE INTERFACE
# ==========================================
def buscar_bio(arroba, api):
    try:
        res = requests.post("https://google.serper.dev/search", 
                            headers={'X-API-KEY': api, 'Content-Type': 'application/json'},
                            data=json.dumps({"q": f'site:instagram.com "{arroba}"', "num": 1}))
        item = res.json().get("organic", [{}])[0]
        return item.get("snippet", "") + " " + item.get("title", "")
    except: return "Sem dados."

def botao_dm(username, script):
    uid = re.sub(r'\W', '', username)
    html = f"""
    <div style="width:100%;">
        <a id="btn_{uid}" href="https://ig.me/m/{username}" target="_blank" rel="noopener"
           onclick="document.getElementById('ta_{uid}').select();document.execCommand('copy');window.open('https://www.instagram.com/{username}/','_blank');"
           style="display:flex;align-items:center;justify-content:center;width:100%;background-color:#FF4B4B;color:white!important;border-radius:8px;padding:8px;font-size:12px;font-weight:600;cursor:pointer;text-decoration:none;height:38px;">
            📋 Copiar + DM
        </a>
        <textarea id="ta_{uid}" style="position:absolute;left:-9999px;">{script if script else ""}</textarea>
    </div>
    """
    components.html(html, height=55)

def card_lead(chumbo, contexto):
    with st.expander(f"🔥 {chumbo['arroba']} - Aprovado", expanded=False):
        user = chumbo['arroba'].replace('@', '').strip()
        col1, col2, col3, col4, col5 = st.columns([1.5, 0.8, 1, 1, 1])
        col1.caption(f"**Motivo:** {chumbo['motivo']}")
        col2.code(user, language=None)
        with col3: botao_dm(user, chumbo.get('script_1', ''))
        
        k_crm, k_bl = f"crm_{chumbo['arroba']}_{contexto}", f"bl_{chumbo['arroba']}_{contexto}"
        
        with col4:
            if not st.session_state.get(k_crm) and st.button("✅ CRM", key=f"btn_c_{k_crm}", use_container_width=True):
                d = chumbo.copy(); d.update({"link_ig": f"https://instagram.com/{user}", "sheet_name": st.session_state["nome_aba"], "status": "Abordado"})
                if enviar_lead_para_planilha(d): 
                    st.session_state[k_crm] = True
                    st.rerun()
            elif st.session_state.get(k_crm): st.success("No CRM")

        with col5:
            if not st.session_state.get(k_bl) and st.button("🚫 BL", key=f"btn_b_{k_bl}", use_container_width=True):
                d = chumbo.copy(); d.update({"link_ig": f"https://instagram.com/{user}", "sheet_name": st.session_state["aba_blacklist"], "status": "Rejeitado"})
                if enviar_lead_para_planilha(d):
                    st.session_state["blacklist_arrobas"].add(chumbo['arroba'])
                    st.session_state[k_bl] = True
                    st.rerun()
            elif st.session_state.get(k_bl): st.warning("Blacklist")
            
        st.divider()
        st.markdown("**Mensagem Gerada:**")
        st.code(chumbo.get('script_1', ''), language="markdown")

# --- LOOP DE PROCESSAMENTO ---
def processar_lote(lista):
    st.session_state["leads_aprovados_tela"] = []
    st.session_state["leads_reprovados_tela"] = []
    barra = st.progress(0)
    for i, arroba in enumerate(lista):
        barra.progress((i + 1) / len(lista), text=f"Analisando {arroba} no Gemini 2.5 Flash...")
        bio = buscar_bio(arroba, st.session_state["api_key_serper"])
        if "Sem dados" not in bio:
            av = analisar_e_gerar_script(arroba, bio, st.session_state["api_key_gemini"], seu_nome, anos_exp, st.session_state.get("pronome_lead", ""))
            if av.get("status") == "APROVADO":
                lead = {"arroba": arroba, "bio": bio, "script_1": av.get("script_1"), "motivo": av.get("motivo")}
                st.session_state["leads_aprovados_tela"].append(lead)
                if arroba not in [l["arroba"] for l in st.session_state["historico_leads"]]:
                    st.session_state["historico_leads"].insert(0, lead)
            else: st.session_state["leads_reprovados_tela"].append({"arroba": arroba, "motivo": av.get("motivo")})
        else: st.session_state["leads_reprovados_tela"].append({"arroba": arroba, "motivo": "Perfil fechado ou sem dados."})
        time.sleep(1.0)
    barra.empty()

# ==========================================
# 🚀 INTERFACE PRINCIPAL
# ==========================================
st.subheader("⚡ B2Scraper Insta - Garimpo High-Ticket")
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Garimpo", "📝 Manual", "📚 Histórico", "📊 CRM"])

with tab1:
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])
    v_nicho = col1.text_input("Nicho:", placeholder="Ex: Arquiteto")
    v_hash = col2.text_input("Hashtag:", placeholder="#decoracao")
    v_loc = col3.text_input("Localização:", placeholder="São Paulo")
    v_qtd = col4.number_input("Qtd:", 5, 50, 15, 5)
    
    if st.button("🚀 Iniciar Busca Inteligente", type="primary", use_container_width=True):
        if not st.session_state.get("api_key_gemini"): st.error("Falta a API do Gemini!")
        else:
            arros, prox = garimpar_perfis_google(v_nicho, v_hash, v_loc, "", "", v_qtd, st.session_state["api_key_serper"])
            if arros: processar_lote(arros)
            else: st.warning("Nenhum perfil novo encontrado.")

    for c in st.session_state["leads_aprovados_tela"]: card_lead(c, "garimpo")

with tab2:
    lista_man = st.text_area("Cole os @arrobas (um por linha):", height=150)
    if st.button("🔥 Processar Lote Manual"):
        if lista_man.strip(): processar_lote([a.strip() for a in lista_man.split("\n") if a.strip()])
    for c in st.session_state["leads_aprovados_tela"]: card_lead(c, "manual")

with tab3:
    if not st.session_state["historico_leads"]: st.info("Histórico vazio.")
    for c in st.session_state["historico_leads"]: card_lead(c, "hist")

with tab4:
    components.iframe("https://docs.google.com/spreadsheets/d/1Ru4E7ArF3UKiPhkqjy0OkrCkdSKzcjHHchQm5v-836g/edit?rm=minimal", height=800, scrolling=True)

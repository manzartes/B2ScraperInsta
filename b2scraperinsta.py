import streamlit as st
import requests
import json
import google.generativeai as genai
import time
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="B2Scraper Insta", page_icon="⚡", layout="wide")

# ==========================================
# 🔑 PUXANDO CHAVES COM SEGURANÇA (SECRETS)
# ==========================================
try:
    CHAVE_SERPER_PADRAO = st.secrets.get("CHAVE_SERPER", "")
    CHAVE_GEMINI_PADRAO = st.secrets.get("CHAVE_GEMINI", "")
    URL_WEBHOOK_PLANILHA = st.secrets.get("WEBHOOK_PLANILHA", "")
except Exception:
    CHAVE_SERPER_PADRAO = ""
    CHAVE_GEMINI_PADRAO = ""
    URL_WEBHOOK_PLANILHA = ""

# --- INICIALIZANDO MEMÓRIAS BLINDADAS ---
if "historico_leads" not in st.session_state:
    st.session_state["historico_leads"] = []
if "ultima_busca_nicho" not in st.session_state:
    st.session_state["ultima_busca_nicho"] = ""
if "ultima_busca_hashtag" not in st.session_state:
    st.session_state["ultima_busca_hashtag"] = ""
if "ultima_busca_local" not in st.session_state:
    st.session_state["ultima_busca_local"] = ""
if "ultima_busca_negativos" not in st.session_state:
    st.session_state["ultima_busca_negativos"] = ""
if "ultima_busca_frase" not in st.session_state:
    st.session_state["ultima_busca_frase"] = ""
if "proxima_pagina" not in st.session_state:
    st.session_state["proxima_pagina"] = 1

if "leads_aprovados_tela" not in st.session_state:
    st.session_state["leads_aprovados_tela"] = []
if "leads_reprovados_tela" not in st.session_state:
    st.session_state["leads_reprovados_tela"] = []

if "blacklist_arrobas" not in st.session_state:
    st.session_state["blacklist_arrobas"] = set()

if "bons_exemplos" not in st.session_state:
    st.session_state["bons_exemplos"] = []
if "maus_exemplos" not in st.session_state:
    st.session_state["maus_exemplos"] = []
if "feedbacks_dados" not in st.session_state:
    st.session_state["feedbacks_dados"] = [] 

# --- SCRIPT DE MENSAGEM PADRÃO ---
if "script_customizado" not in st.session_state:
    st.session_state["script_customizado"] = """Olá, [PRONOME_E_NOME]. Tudo bem?
Espero que sim.

Aqui é o [SEU_NOME], muito prazer. Eu trabalho há mais de [ANOS_EXP] anos ajudando empresários a serem percebidos como autoridade, conseguirem vender mais, cobrando melhor e com maior lucro.

Me deparei com seu perfil e gostei muito do conteúdo que você gera sobre [ÁREA X], principalmente do seu foco em [ESPECIALIDADE].

Vi que o seu perfil tem várias semelhanças com profissionais que atendo, mas também percebi alguns pontos que podem estar limitando a forma como o mercado te enxerga — e isso normalmente impacta diretamente no quanto você consegue cobrar e nas oportunidades que chegam até você.

Posso compartilhar essas observações?"""

# --- FUNÇÕES DE MEMÓRIA PERMANENTE ---
def puxar_memoria_ia():
    webhook = st.session_state.get("url_webhook", URL_WEBHOOK_PLANILHA)
    if not webhook: return {"bons": [], "maus": []}
    try:
        res = requests.get(f"{webhook}?acao=memoria")
        if res.ok:
            return res.json()
    except Exception:
        pass
    return {"bons": [], "maus": []}

def salvar_feedback_planilha(arroba, feedback_tipo, bio):
    webhook = st.session_state.get("url_webhook", URL_WEBHOOK_PLANILHA)
    if not webhook: return
    dados = {
        "tipo": "feedback",
        "sheet_name": "MemoriaIA",
        "arroba": arroba,
        "feedback": feedback_tipo,
        "bio": bio
    }
    try:
        requests.post(webhook, json=dados)
    except:
        pass

if "memoria_carregada" not in st.session_state:
    if URL_WEBHOOK_PLANILHA:
        with st.spinner("A carregar o cérebro da IA da Nuvem..."):
            memoria_nuvem = puxar_memoria_ia()
            st.session_state["bons_exemplos"] = memoria_nuvem.get("bons", [])
            st.session_state["maus_exemplos"] = memoria_nuvem.get("maus", [])
    st.session_state["memoria_carregada"] = True


# --- Layout do Cabeçalho ---
col_titulo, col_botoes = st.columns([3, 1])
with col_titulo:
    st.title("⚡ B2Scraper Insta")
    st.markdown("Encontre perfis, qualifique com IA e mande para a aba certa do CRM com 1 clique.")
with col_botoes:
    st.write("") 
    st.write("")
    st.link_button("📊 Planilha de Controle", "https://docs.google.com/spreadsheets/d/1Ru4E7ArF3UKiPhkqjy0OkrCkdSKzcjHHchQm5v-836g/edit?gid=1121870777#gid=1121870777", use_container_width=True)
    st.link_button("💼 B2Scraper LinkedIn", "https://b2scraper.streamlit.app/", use_container_width=True)
    st.link_button("🕸️ B2Scraper Web", "https://b2scraperweb.streamlit.app/", use_container_width=True)

# ==========================================
# ⚙️ MENU LATERAL ORGANIZADO
# ==========================================
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    
    with st.expander("🎯 Destino na Planilha (CRM)", expanded=True):
        if "url_webhook" not in st.session_state:
            st.session_state["url_webhook"] = URL_WEBHOOK_PLANILHA
        if "nome_aba" not in st.session_state:
            st.session_state["nome_aba"] = "ABRIL/26"
        url_webhook = st.text_input("URL do Webhook:", type="password", value=st.session_state["url_webhook"])
        nome_aba = st.text_input("Aba de Entrada (CRM):", value=st.session_state["nome_aba"])
        st.session_state["url_webhook"] = url_webhook
        st.session_state["nome_aba"] = nome_aba

    with st.expander("🚫 Gerenciar Blacklist", expanded=False):
        if "aba_blacklist" not in st.session_state:
            st.session_state["aba_blacklist"] = "BLACKLIST"
        aba_blacklist = st.text_input("Aba da Blacklist:", value=st.session_state["aba_blacklist"])
        st.session_state["aba_blacklist"] = aba_blacklist
        blacklist_texto = st.text_area("Colar arrobas manuais:", height=60, placeholder="@joao")
        blacklist_manual = {a.strip().replace("https://www.instagram.com/", "@").replace("/", "") for a in blacklist_texto.split("\n") if a.strip()}

    with st.expander("🔑 Chaves de API", expanded=False):
        api_key_serper = st.text_input("API Key do Serper:", type="password", value=st.session_state.get("api_key_serper", CHAVE_SERPER_PADRAO))
        api_key_gemini = st.text_input("API Key do Gemini:", type="password", value=st.session_state.get("api_key_gemini", CHAVE_GEMINI_PADRAO))
        st.session_state["api_key_serper"] = api_key_serper
        st.session_state["api_key_gemini"] = api_key_gemini

    with st.expander("👤 Seu Perfil e Abordagem", expanded=False):
        seu_nome = st.text_input("Seu Nome:", value="Henrique Durant")
        anos_exp = st.text_input("Anos de Experiência:", value="5")
        pronome_lead = st.text_input("Pronome do Lead (Opcional):", placeholder="Ex: Dr.")
        st.session_state["pronome_lead"] = pronome_lead
        
        st.markdown("**Script de Abordagem Personalizado:**")
        st.session_state["script_customizado"] = st.text_area("Edite seu script (Use [PRONOME_E_NOME], [ÁREA X], [ESPECIALIDADE]):", 
                                                             value=st.session_state["script_customizado"], height=300)
        
    st.divider()
    # CORREÇÃO AQUI: Mudado de 'bons_examples' para 'bons_exemplos' para bater com a inicialização
    st.caption(f"🧠 IA possui na memória: {len(st.session_state['bons_exemplos'])} likes / {len(st.session_state['maus_exemplos'])} dislikes.")

# --- ENVIAR PARA GOOGLE SHEETS ---
def enviar_lead_para_planilha(lead_dados):
    webhook = st.session_state["url_webhook"]
    if not webhook: return False
    try:
        resposta = requests.post(webhook, json=lead_dados)
        return resposta.ok and "Sucesso" in resposta.text
    except: return False

# --- PUXAR BLACKLIST ---
def puxar_blacklist_automatica():
    webhook = st.session_state["url_webhook"]; aba = st.session_state["aba_blacklist"]
    if not webhook or not aba: return set()
    try:
        resposta = requests.get(f"{webhook}?aba={aba}")
        if resposta.ok:
            dados = resposta.json()
            if "leads" in dados:
                return {str(a).strip().replace("https://www.instagram.com/", "@").replace("/", "") for a in dados["leads"] if str(a).strip()}
    except: pass
    return set()

# --- MOTOR DE GARIMPO (REFORÇADO) ---
def garimpar_perfis_google(profissao, hashtag, localizacao, termos_negativos, frase_exata, qtd, api_serper, pagina_inicial=1):
    url = "https://google.serper.dev/search"
    query = 'site:instagram.com -inurl:p -inurl:reel -inurl:explore -inurl:tags'
    if profissao: query += f' "{profissao}"'
    if hashtag: query += f' {hashtag if hashtag.startswith("#") else f"#{hashtag}"}'
    if localizacao: query += f' "{localizacao}"'
    if frase_exata: query += f' intext:"{frase_exata}"'
    if termos_negativos:
        for negativo in [t.strip() for t in termos_negativos.split(",") if t.strip()]:
            query += f' -{negativo}'
    
    arrobas_encontrados = []
    palavras_ignoradas = ['p', 'reel', 'reels', 'explore', 'tags', 'stories', 'tv', 'channel', 'about', 'legal', 'directory']
    blacklist_total = st.session_state["blacklist_arrobas"].union(blacklist_manual).union(puxar_blacklist_automatica())
    
    # Busca profunda para garantir a quantidade
    limite_paginas = 20
    ultima_pagina_pesquisada = pagina_inicial
    
    for pagina in range(pagina_inicial, pagina_inicial + limite_paginas):
        ultima_pagina_pesquisada = pagina
        if len(arrobas_encontrados) >= qtd: break
        payload = json.dumps({"q": query, "page": pagina, "num": 10}) 
        headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
        try:
            res = requests.post(url, headers=headers, data=payload)
            if not res.ok: break
            organicos = res.json().get("organic", [])
            if not organicos: break
            for item in organicos:
                match = re.search(r'instagram\.com/([^/?]+)', item.get("link", ""))
                if match:
                    username = match.group(1).strip()
                    if username.lower() not in palavras_ignoradas:
                        user = f"@{username}"
                        if user not in blacklist_total and user not in arrobas_encontrados:
                            arrobas_encontrados.append(user)
                        if len(arrobas_encontrados) >= qtd: break
        except: break
        time.sleep(0.4)
    return arrobas_encontrados[:qtd], ultima_pagina_pesquisada + 1

# --- CÉREBRO DA IA (GEMINI 2.5 FLASH + SCRIPT DINÂMICO) ---
def analisar_e_gerar_script(arroba, snippet_google, api_gemini, nome_bdr, exp_bdr, pronome_lead):
    try:
        genai.configure(api_key=api_gemini)
        modelo = genai.GenerativeModel('gemini-2.5-flash')
        
        treinamento = ""
        if st.session_state["bons_exemplos"]:
            bons = "\n- ".join(st.session_state["bons_exemplos"][-3:]) 
            treinamento += f"\n\n🚨 GOSTOS DO USUÁRIO:\n- {bons}"
        if st.session_state["maus_exemplos"]:
            maus = "\n- ".join(st.session_state["maus_exemplos"][-3:])
            treinamento += f"\n\n🚨 REPROVADOS PELO USUÁRIO:\n- {maus}"
            
        script_base = st.session_state["script_customizado"]
            
        prompt = f"""
        Atue como {nome_bdr}, BDR especialista. Analise o lead de High-Ticket.
        ICP: Donos de empresas, Profissionais liberais, Médicos, Advogados, Consultores.

        CRITÉRIOS: Reprovar perfis privados, amadores (sem camisa), ou com > 50k seguidores.
        {treinamento}

        Resumo do Google para {arroba}: "{snippet_google}"

        Se aprovado, preencha este modelo de script EXATAMENTE (sem inventar frases extras):
        ---
        {script_base}
        ---

        REGRAS:
        1. Troque [PRONOME_E_NOME] por "{pronome_lead}" (flexione conforme gênero) + Primeiro Nome.
        2. Troque [ÁREA X], [ESPECIALIDADE].
        3. [SEU_NOME] = {nome_bdr}, [ANOS_EXP] = {exp_bdr}.

        Retorne APENAS um JSON:
        {{
        "status": "APROVADO" ou "REPROVADO",
        "motivo": "justificativa curta",
        "script_1": "texto final preenchido"
        }}
        """
        resposta = modelo.generate_content(prompt)
        texto_json = resposta.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_json)
    except Exception as e:
        return {"status": "ERRO", "motivo": str(e)}

def buscar_bio_no_google(arroba, api_serper):
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f'site:instagram.com "{arroba}"', "num": 1})
    headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        dados = res.json()
        if "organic" in dados and len(dados["organic"]) > 0:
            return dados["organic"][0].get("snippet", "") + " " + dados["organic"][0].get("title", "")
        return "Nenhuma informação."
    except: return "Erro ao buscar."

# --- BOTÃO MÁGICO ---
def botao_copiar_e_abrir_dm(username, script):
    uid = re.sub(r'[^a-zA-Z0-9]', '', username)
    script_safe = json.dumps(script if script else "")
    html_botao = f"""
    <div style="width:100%;">
        <a id="btn_dm_{uid}" href="https://ig.me/m/{username}" target="_blank" rel="noopener noreferrer"
           onclick="copiarEAbrirTudo_{uid}(event)"
           style="display:flex;align-items:center;justify-content:center;width:100%;background-color:#FF4B4B;color:white!important;border-radius:8px;padding:8px;font-size:13px;font-weight:600;cursor:pointer;font-family:sans-serif;height:38px;text-decoration:none;">
            📋 Copiar + Perfil + DM
        </a>
        <textarea id="ta_{uid}" style="position:absolute;left:-9999px;">{script if script else ""}</textarea>
    </div>
    <script>
    function copiarEAbrirTudo_{uid}(event) {{
        const btn = document.getElementById('btn_dm_{uid}');
        const ta = document.getElementById('ta_{uid}');
        try {{
            ta.focus(); ta.select(); document.execCommand('copy');
            if (navigator.clipboard) {{ navigator.clipboard.writeText({script_safe}).catch(function() {{}}); }}
            btn.innerHTML = '✅ Copiado! Abrindo...'; btn.style.backgroundColor = '#28a745';
        }} catch (err) {{ btn.innerHTML = '⚠️ Abrindo...'; }}
        window.open('https://www.instagram.com/{username}/', '_blank');
        setTimeout(function() {{ btn.innerHTML = '📋 Copiar + Perfil + DM'; btn.style.backgroundColor = '#FF4B4B'; }}, 2500);
        return true;
    }}
    </script>
    """
    components.html(html_botao, height=55)

# --- DESIGN DO CARD ---
def desenhar_card_lead(chumbo, contexto="geral"):
    with st.expander(f"🔥 {chumbo['arroba']} - ICP Aprovado", expanded=False):
        username_limpo = chumbo['arroba'].replace('@', '').strip()
        link_ig = f"https://www.instagram.com/{username_limpo}/"
        col1, col2, col3, col4, col5 = st.columns([1.5, 0.8, 1, 1, 1])
        with col1: st.caption(f"**Motivo:** {chumbo['motivo']}")
        with col2: st.code(username_limpo, language=None)
        with col3: botao_copiar_e_abrir_dm(username_limpo, chumbo.get('script_1', ''))
        
        estado_crm_key = f"estado_crm_{chumbo['arroba']}_{contexto}"
        estado_bl_key = f"estado_bl_{chumbo['arroba']}_{contexto}"
        if estado_crm_key not in st.session_state: st.session_state[estado_crm_key] = False
        if estado_bl_key not in st.session_state: st.session_state[estado_bl_key] = False

        with col4:
            if not st.session_state[estado_crm_key] and not st.session_state[estado_bl_key]:
                if st.button("✅ CRM", key=f"btn_crm_{chumbo['arroba']}_{contexto}", use_container_width=True):
                    d = chumbo.copy(); d.update({"link_ig": link_ig, "sheet_name": st.session_state["nome_aba"], "status": "Abordado"})
                    if enviar_lead_para_planilha(d):
                        st.session_state["blacklist_arrobas"].add(chumbo['arroba'])
                        st.session_state[estado_crm_key] = True; st.rerun() 
            elif st.session_state[estado_crm_key]: st.success("✅ No CRM!")

        with col5:
            if not st.session_state[estado_crm_key] and not st.session_state[estado_bl_key]:
                if st.button("🚫 BL", key=f"btn_bl_{chumbo['arroba']}_{contexto}", use_container_width=True):
                    d = chumbo.copy(); d.update({"link_ig": link_ig, "sheet_name": st.session_state["aba_blacklist"], "status": "Rejeitado"})
                    if enviar_lead_para_planilha(d):
                        st.session_state["blacklist_arrobas"].add(chumbo['arroba'])
                        st.session_state[estado_bl_key] = True; st.rerun()
            elif st.session_state[estado_bl_key]: st.warning("🚫 Na BL!")
            
        st.divider()
        st.code(chumbo.get('script_1', ''), language="markdown")
        st.divider()
        if chumbo['arroba'] not in st.session_state["feedbacks_dados"]:
            c_f1, c_f2, _ = st.columns([1, 1, 2])
            if c_f1.button("👍 Sim", key=f"up_{chumbo['arroba']}_{contexto}"):
                st.session_state["bons_exemplos"].append(chumbo.get('bio', ''))
                st.session_state["feedbacks_dados"].append(chumbo['arroba'])
                salvar_feedback_planilha(chumbo['arroba'], "Like", chumbo.get('bio', ''))
                st.rerun()
            if c_f2.button("👎 Não", key=f"down_{chumbo['arroba']}_{contexto}"):
                st.session_state["maus_exemplos"].append(chumbo.get('bio', ''))
                st.session_state["feedbacks_dados"].append(chumbo['arroba'])
                salvar_feedback_planilha(chumbo['arroba'], "Dislike", chumbo.get('bio', ''))
                st.rerun()
        else: st.success("✅ Feedback guardado!")

# --- PROCESSAMENTO ---
def processar_lista_arrobas(lista_de_arrobas):
    st.session_state["leads_aprovados_tela"] = []
    st.session_state["leads_reprovados_tela"] = []
    barra = st.progress(0)
    for i, arroba in enumerate(lista_de_arrobas):
        barra.progress((i + 1) / len(lista_de_arrobas), text=f"Analisando {arroba}...")
        st.session_state["blacklist_arrobas"].add(arroba)
        bio = buscar_bio_no_google(arroba, st.session_state["api_key_serper"])
        if bio and "Erro" not in bio and "Nenhuma" not in bio:
            av = analisar_e_gerar_script(arroba, bio, st.session_state["api_key_gemini"], seu_nome, anos_exp, st.session_state.get("pronome_lead", ""))
            if av.get("status") == "APROVADO":
                lead = {"arroba": arroba, "bio": bio, "script_1": av.get("script_1"), "motivo": av.get("motivo")}
                st.session_state["leads_aprovados_tela"].append(lead)
                if arroba not in [l["arroba"] for l in st.session_state["historico_leads"]]:
                    st.session_state["historico_leads"].insert(0, lead) 
            else: st.session_state["leads_reprovados_tela"].append({"arroba": arroba, "motivo": av.get("motivo")})
        else: st.session_state["leads_reprovados_tela"].append({"arroba": arroba, "motivo": "Sem dados."})
        time.sleep(1.0)
    barra.empty()

def renderizar_resultados_garimpo(contexto_render):
    if st.session_state["leads_aprovados_tela"]:
        st.divider(); st.subheader(f"✅ {len(st.session_state['leads_aprovados_tela'])} Leads Aprovados")
        for c in st.session_state["leads_aprovados_tela"]: desenhar_card_lead(c, contexto_render)
    if st.session_state["leads_reprovados_tela"]:
        st.subheader(f"❌ {len(st.session_state['leads_reprovados_tela'])} Descartados")
        for l in st.session_state["leads_reprovados_tela"]: st.write(f"- **{l['arroba']}**: {l['motivo']}")

# --- ABAS ---
aba_garimpo, aba_busca, aba_historico, aba_crm = st.tabs(["🔍 Garimpo", "📝 Manual", "📚 Histórico", "📊 CRM"])

with aba_garimpo:
    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 1])
    nicho = c1.text_input("Nicho:", placeholder="Arquiteto")
    hash_t = c2.text_input("Hashtag:", placeholder="#decoracao")
    loc = c3.text_input("Localização:", placeholder="São Paulo")
    qtd = c4.number_input("Qtd:", 5, 50, 15, 5)
    with st.expander("🛠️ Filtros Avançados", expanded=False):
        f1, f2 = st.columns(2)
        neg = f1.text_input("Excluir:", placeholder="estudante")
        frase = f2.text_input("Frase na Bio:", placeholder='Agende consulta')
    if st.button("🔍 Iniciar Busca", type="primary", use_container_width=True):
        if not nicho and not hash_t: st.warning("Preencha Nicho ou Hashtag.")
        else:
            st.session_state.update({"ultima_busca_nicho": nicho, "ultima_busca_hashtag": hash_t, "ultima_busca_local": loc, "ultima_busca_negativos": neg, "ultima_busca_frase": frase, "proxima_pagina": 1})
            with st.spinner("Garimpando..."):
                arros, px = garimpar_perfis_google(nicho, hash_t, loc, neg, frase, qtd, st.session_state["api_key_serper"], 1)
                st.session_state["proxima_pagina"] = px
            if arros: processar_lista_arrobas(arros)
    if st.session_state["ultima_busca_nicho"]:
        if st.button("➕ Mais 10 Leads", use_container_width=True):
            with st.spinner("Buscando mais..."):
                arros, px = garimpar_perfis_google(st.session_state["ultima_busca_nicho"], st.session_state["ultima_busca_hashtag"], st.session_state["ultima_busca_local"], st.session_state["ultima_busca_negativos"], st.session_state["ultima_busca_frase"], 10, st.session_state["api_key_serper"], st.session_state["proxima_pagina"])
                st.session_state["proxima_pagina"] = px
            if arros: processar_lista_arrobas(arros)
    renderizar_resultados_garimpo("garimpo")

with aba_busca:
    lista_man = st.text_area("Cole os @arrobas:", height=150)
    if st.button("🚀 Processar Lote", type="primary"):
        if lista_man.strip(): processar_lista_arrobas([a.strip() for a in lista_man.split("\n") if a.strip()])
    renderizar_resultados_garimpo("manual")

with aba_historico:
    if not st.session_state["historico_leads"]: st.info("Sem leads.")
    else:
        for c in st.session_state["historico_leads"]: desenhar_card_lead(c, "historico")

with aba_crm:
    components.iframe("https://docs.google.com/spreadsheets/d/1Ru4E7ArF3UKiPhkqjy0OkrCkdSKzcjHHchQm5v-836g/edit?rm=minimal", height=800, scrolling=True)

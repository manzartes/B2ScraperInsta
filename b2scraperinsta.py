import streamlit as st
import requests
import json
import google.generativeai as genai
import time
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="B2SCraper Insta", page_icon="⚡", layout="wide")

# ==========================================
# 🔑 PUXANDO CHAVES COM SEGURANÇA (SECRETS)
# ==========================================
try:
    CHAVE_SERPER_PADRAO = st.secrets.get("CHAVE_SERPER", "")
    CHAVE_GEMINI_PADRAO = st.secrets.get("CHAVE_GEMINI", "")
    URL_WEBHOOK_PLANILHA = st.secrets.get("WEBHOOK_PLANILHA", "")
    NOME_ABA_PADRAO = st.secrets.get("NOME_ABA", "Página1")
except Exception:
    CHAVE_SERPER_PADRAO = ""
    CHAVE_GEMINI_PADRAO = ""
    URL_WEBHOOK_PLANILHA = ""
    NOME_ABA_PADRAO = "MARÇO/26"

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

# Arrays que agora serão preenchidos pela Planilha
if "bons_exemplos" not in st.session_state:
    st.session_state["bons_exemplos"] = []
if "maus_exemplos" not in st.session_state:
    st.session_state["maus_exemplos"] = []
if "feedbacks_dados" not in st.session_state:
    st.session_state["feedbacks_dados"] = [] 

# --- FUNÇÕES DE MEMÓRIA PERMANENTE (PLANILHA) ---
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

# Sincroniza a memória no início da sessão
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
    st.link_button("💼 B2ScraperLinkedIn", "https://b2scraper.streamlit.app/", use_container_width=True)

# ==========================================
# ⚙️ MENU LATERAL ORGANIZADO (GAVETAS)
# ==========================================
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    
    with st.expander("🎯 Destino na Planilha (CRM)", expanded=True):
        if "url_webhook" not in st.session_state:
            st.session_state["url_webhook"] = URL_WEBHOOK_PLANILHA
        if "nome_aba" not in st.session_state:
            st.session_state["nome_aba"] = NOME_ABA_PADRAO
            
        url_webhook = st.text_input("URL do Webhook:", type="password", value=st.session_state["url_webhook"])
        nome_aba = st.text_input("Aba de Entrada (CRM):", value=st.session_state["nome_aba"], help="Para onde vão os leads aprovados.")
        
        st.session_state["url_webhook"] = url_webhook
        st.session_state["nome_aba"] = nome_aba

    with st.expander("🚫 Gerenciar Blacklist", expanded=False):
        st.markdown("<small>Aba da planilha exclusiva para a Lista Negra.</small>", unsafe_allow_html=True)
        if "aba_blacklist" not in st.session_state:
            st.session_state["aba_blacklist"] = "BLACKLIST"
            
        aba_blacklist = st.text_input("Aba da Blacklist:", value=st.session_state["aba_blacklist"], help="Tem que existir na planilha do Sheets.")
        st.session_state["aba_blacklist"] = aba_blacklist
        
        st.markdown("<small><i>Arrobas manuais avulsos:</i></small>", unsafe_allow_html=True)
        blacklist_texto = st.text_area("Colar arrobas:", height=60, placeholder="@joao\n@clinica_xyz")
        blacklist_manual = {a.strip().replace("https://www.instagram.com/", "@").replace("/", "") for a in blacklist_texto.split("\n") if a.strip()}

    with st.expander("🔑 Chaves de API", expanded=False):
        if "api_key_serper" not in st.session_state:
            st.session_state["api_key_serper"] = CHAVE_SERPER_PADRAO
        if "api_key_gemini" not in st.session_state:
            st.session_state["api_key_gemini"] = CHAVE_GEMINI_PADRAO
            
        api_key_serper = st.text_input("API Key do Serper:", type="password", value=st.session_state["api_key_serper"])
        api_key_gemini = st.text_input("API Key do Gemini:", type="password", value=st.session_state["api_key_gemini"])
        
        st.session_state["api_key_serper"] = api_key_serper
        st.session_state["api_key_gemini"] = api_key_gemini

    with st.expander("👤 Seu Perfil (BDR)", expanded=False):
        seu_nome = st.text_input("Seu Nome:", value="Henrique Durant")
        anos_exp = st.text_input("Anos de Experiência:", value="5")
        
    st.divider()
    st.caption(f"🧠 IA possui na memória: {len(st.session_state['bons_exemplos'])} likes / {len(st.session_state['maus_exemplos'])} dislikes.")

# --- ENVIAR PARA GOOGLE SHEETS ---
def enviar_lead_para_planilha(lead_dados):
    webhook = st.session_state["url_webhook"]
    if not webhook:
        st.error("Configure a URL do Webhook na barra lateral primeiro!")
        return False
    try:
        resposta = requests.post(webhook, json=lead_dados)
        if resposta.ok and "Sucesso" in resposta.text:
            return True
        else:
            st.error(f"Erro na Planilha: {resposta.text}")
            return False
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return False

# --- PUXAR BLACKLIST DA PLANILHA ---
def puxar_blacklist_automatica():
    webhook = st.session_state["url_webhook"]
    aba = st.session_state["aba_blacklist"]
    if not webhook or not aba:
        return set()
    try:
        resposta = requests.get(f"{webhook}?aba={aba}")
        if resposta.ok:
            dados = resposta.json()
            if "leads" in dados:
                lista_suja = dados["leads"]
                lista_limpa = {str(a).strip().replace("https://www.instagram.com/", "@").replace("/", "") for a in lista_suja if str(a).strip()}
                return lista_limpa
    except Exception:
        pass
    return set()

# --- MOTOR DE GARIMPO (COM FILTROS AVANÇADOS) ---
def garimpar_perfis_google(profissao, hashtag, localizacao, termos_negativos, frase_exata, qtd, api_serper, pagina_inicial=1):
    url = "https://google.serper.dev/search"
    
    # HACK AVANÇADO: Proibir fotos e reels
    query = 'site:instagram.com -inurl:p -inurl:reel -inurl:explore -inurl:tags'
    
    if profissao:
        query += f' "{profissao}"'
    if hashtag:
        hash_term = hashtag if hashtag.startswith("#") else f"#{hashtag}"
        query += f' {hash_term}'
    if localizacao:
        query += f' "{localizacao}"'
        
    # Aplicando Filtros Avançados
    if frase_exata:
        query += f' intext:"{frase_exata}"'
    if termos_negativos:
        lista_negativos = [t.strip() for t in termos_negativos.split(",") if t.strip()]
        for negativo in lista_negativos:
            query += f' -{negativo}'
    
    arrobas_encontrados = []
    palavras_ignoradas = ['p', 'reel', 'reels', 'explore', 'tags', 'stories', 'tv', 'channel', 'about', 'legal', 'directory']
    
    barra_busca = st.progress(0, text="Sincronizando Blacklist com a Planilha...")
    blacklist_da_nuvem = puxar_blacklist_automatica()
    blacklist_total = st.session_state["blacklist_arrobas"].union(blacklist_manual).union(blacklist_da_nuvem)
    
    paginas_necessarias = (qtd // 10) + 4 
    ultima_pagina_pesquisada = pagina_inicial
    
    for pagina in range(pagina_inicial, pagina_inicial + paginas_necessarias):
        ultima_pagina_pesquisada = pagina
        if len(arrobas_encontrados) >= qtd:
            break
            
        progresso = min((pagina - pagina_inicial) / paginas_necessarias, 1.0)
        barra_busca.progress(progresso, text=f"Lendo página {pagina} do Google...")
        
        payload = json.dumps({"q": query, "page": pagina, "num": 10}) 
        headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
        
        try:
            res = requests.post(url, headers=headers, data=payload)
            if not res.ok:
                st.error(f"Erro na API do Serper: {res.text}")
                break
                
            dados = res.json()
            organicos = dados.get("organic", [])
            
            if not organicos:
                break 
                
            for item in organicos:
                link = item.get("link", "")
                match = re.search(r'instagram\.com/([^/?]+)', link)
                if match:
                    username = match.group(1).strip()
                    if username.lower() not in palavras_ignoradas:
                        arroba_formatado = f"@{username}"
                        
                        if arroba_formatado not in blacklist_total and arroba_formatado not in arrobas_encontrados:
                            arrobas_encontrados.append(arroba_formatado)
                        
                        if len(arrobas_encontrados) >= qtd:
                            break
                            
        except Exception:
            break
            
        time.sleep(0.5) 
        
    barra_busca.empty()
    return arrobas_encontrados[:qtd], ultima_pagina_pesquisada + 1

# --- CÉREBRO DA IA (ENXUTO E COM PERSONA CORRIGIDA) ---
def analisar_e_gerar_script(arroba, snippet_google, api_gemini, nome_bdr, exp_bdr):
    try:
        genai.configure(api_key=api_gemini)
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not modelos_disponiveis:
            return {"status": "ERRO", "motivo": "Sem acesso à IA."}
            
        modelo_escolhido = modelos_disponiveis[0]
        for nome in modelos_disponiveis:
            if 'flash' in nome:
                modelo_escolhido = nome
                
        modelo = genai.GenerativeModel(modelo_escolhido.replace("models/", ""))
        
        treinamento_extra = ""
        if st.session_state["bons_exemplos"]:
            bons = "\n- ".join(st.session_state["bons_exemplos"][-3:]) 
            treinamento_extra += f"\n\n🚨 ATENÇÃO! O utilizador GOSTOU destes perfis no passado. APROVE parecidos:\n- {bons}"
        if st.session_state["maus_exemplos"]:
            maus = "\n- ".join(st.session_state["maus_exemplos"][-3:])
            treinamento_extra += f"\n\n🚨 ATENÇÃO! O utilizador REPROVOU estes perfis no passado. REPROVE parecidos:\n- {maus}"
        
        prompt = f"""
        Você atua como {nome_bdr}, um BDR de High-Ticket especialista em qualificação de leads. A empresa vende a mentoria "Código do Valor".
        
        O seu ICP EXATO é: Dono de pequena/média empresa, Profissional liberal, Consultor/mentor, Médico/odontólogo, Advogado, Corretor/assessor, Gestor/comercial, Executivo, Engenheiro/arquiteto.

        CRITÉRIOS:
        1. Foto: Se amadora/inadequada (ex: sem camisa), REPROVAR.
        2. Seguidores: Ideal 2k a 50k. MAIS de 50k REPROVAR.
        3. Bio bagunçada ou Posicionamento fraco: APROVAR.
        4. Perfil Privado: Se "This account is private" ou "Conta privada", REPROVAR IMEDIATAMENTE.
        *Atenção*: Se não houver dados exatos para reprovar, APROVE.
        {treinamento_extra}

        Resumo do Google para a conta {arroba}: "{snippet_google}"

        Sua tarefa: Descubra o Nome e a Área/Especialidade. Avalie se é ICP (APROVADO ou REPROVADO). Se APROVADO, gere APENAS O SCRIPT INICIAL de abordagem.
        
        🚨 REGRAS EXTREMAS: 
        1. Mantenha as QUEBRAS DE LINHA (parágrafos) EXATAMENTE como nos modelos abaixo. No JSON, use "\\n\\n" para representar essas quebras de linha.
        2. Substitua APENAS os campos [NOME], [ÁREA X] e [ESPECIALIDADE]. 
        3. É expressamente PROIBIDO alterar o nome "{nome_bdr}" ou os anos de experiência "{exp_bdr}". Mantenha exatamente como eu escrevi no modelo.

        [SCRIPT INICIAL 1 - COM ESPECIALIDADE]
        Olá, [NOME]. Tudo bem?
        Espero que sim.
        
        Aqui é o {nome_bdr}, muito prazer. Eu trabalho há mais de {exp_bdr} anos ajudando empresários a serem percebidos como autoridade, conseguirem vender mais, cobrando melhor e com maior lucro.
        
        Me deparei com seu perfil e gostei muito do conteúdo que você gera sobre [ÁREA X], principalmente do seu foco em [ESPECIALIDADE].
        
        Vi que o seu perfil tem várias semelhanças com profissionais que atendo, mas também percebi alguns pontos que podem estar limitando a forma como o mercado te enxerga — e isso normalmente impacta diretamente no quanto você consegue cobrar e nas oportunidades que chegam até você.
        
        Posso compartilhar essas observações?

        [SCRIPT INICIAL 2 - SEM ESPECIALIDADE]
        Olá, [NOME]. Tudo bem?
        Espero que sim.
        
        Aqui é o {nome_bdr}, muito prazer. Eu trabalho há mais de {exp_bdr} anos ajudando empresários a serem percebidos como autoridade, conseguirem vender mais, cobrando melhor e com maior lucro.
        
        Me deparei com seu perfil e gostei muito do conteúdo que você gera sobre [ÁREA X].
        
        Vi que o seu perfil tem várias semelhanças com profissionais que atendo, mas também percebi alguns pontos que podem estar limitando a forma como o mercado te enxerga — e isso normalmente impacta diretamente no quanto você consegue cobrar e nas oportunidades que chegam até você.
        
        Posso compartilhar essas observações?

        Retorne APENAS um objeto JSON válido (sem marcação markdown):
        "status": "APROVADO" ou "REPROVADO",
        "motivo": "justificativa curta",
        "script_1": "texto ou vazio"
        """
        
        resposta = modelo.generate_content(prompt)
        texto_json = resposta.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_json)
    except Exception as e:
        return {"status": "ERRO", "motivo": f"Falha na IA: {e}"}

def buscar_bio_no_google(arroba, api_serper):
    url = "https://google.serper.dev/search"
    query = f'site:instagram.com "{arroba}"'
    payload = json.dumps({"q": query, "num": 1})
    headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=payload)
        dados = res.json()
        if "organic" in dados and len(dados["organic"]) > 0:
            return dados["organic"][0].get("snippet", "") + " " + dados["organic"][0].get("title", "")
        return "Nenhuma informação."
    except:
        return "Erro ao buscar."

# ==========================================
# 🎨 DESIGN DA CAIXA DO LEAD
# ==========================================
def desenhar_card_lead(chumbo, contexto="geral"):
    with st.expander(f"🔥 {chumbo['arroba']} - ICP Aprovado", expanded=False):
        username_limpo = chumbo['arroba'].replace('@', '').strip()
        username_limpo = re.sub(r'(https?://)?(www\.)?instagram\.com/', '', username_limpo)
        username_limpo = username_limpo.replace('/', '') 
        link_ig = f"https://www.instagram.com/{username_limpo}/"
        
        col1, col2, col3, col4, col5 = st.columns([1.5, 0.8, 1, 1, 1])
        with col1:
            st.caption(f"**Motivo:** {chumbo['motivo']}")
        with col2:
            st.code(username_limpo, language=None)
        with col3:
            st.link_button("👉 Abrir Insta", link_ig, use_container_width=True, type="primary")
        
        estado_crm_key = f"estado_crm_{chumbo['arroba']}_{contexto}"
        estado_bl_key = f"estado_bl_{chumbo['arroba']}_{contexto}"
        
        if estado_crm_key not in st.session_state:
            st.session_state[estado_crm_key] = False
        if estado_bl_key not in st.session_state:
            st.session_state[estado_bl_key] = False

        with col4:
            if not st.session_state[estado_crm_key] and not st.session_state[estado_bl_key]:
                if st.button("✅ CRM", key=f"btn_crm_{chumbo['arroba']}_{contexto}", use_container_width=True):
                    dados_crm = chumbo.copy()
                    dados_crm["link_ig"] = link_ig
                    dados_crm["sheet_name"] = st.session_state["nome_aba"]
                    dados_crm["status"] = "Abordado"
                    
                    dados_bl = chumbo.copy()
                    dados_bl["link_ig"] = link_ig
                    dados_bl["sheet_name"] = st.session_state["aba_blacklist"]
                    dados_bl["status"] = "Foi pro CRM"
                    
                    if enviar_lead_para_planilha(dados_crm):
                        if st.session_state["nome_aba"] != st.session_state["aba_blacklist"]:
                            enviar_lead_para_planilha(dados_bl)
                            
                        st.session_state["blacklist_arrobas"].add(chumbo['arroba'])
                        st.session_state[estado_crm_key] = True
                        st.toast(f"Lead salvo no CRM e enviado para a Blacklist!", icon="✅")
                        st.rerun() 
            elif st.session_state[estado_crm_key]:
                st.success("✅ No CRM!")

        with col5:
            if not st.session_state[estado_crm_key] and not st.session_state[estado_bl_key]:
                if st.button("🚫 Blacklist", key=f"btn_bl_{chumbo['arroba']}_{contexto}", use_container_width=True):
                    dados_bl = chumbo.copy()
                    dados_bl["link_ig"] = link_ig
                    dados_bl["sheet_name"] = st.session_state["aba_blacklist"]
                    dados_bl["status"] = "Rejeitado"
                    
                    if enviar_lead_para_planilha(dados_bl):
                        st.session_state["blacklist_arrobas"].add(chumbo['arroba'])
                        st.session_state[estado_bl_key] = True
                        st.toast(f"Lead enviado direto para a Blacklist!", icon="🚫")
                        st.rerun()
            elif st.session_state[estado_bl_key]:
                st.warning("🚫 Na Blacklist!")
            
        st.divider()
        st.markdown("**Mensagem de Abordagem**")
        st.code(chumbo.get('script_1', ''), language="markdown")
        st.divider()
        
        st.markdown("**A IA acertou neste perfil? (Ajude-a a aprender)**")
        if chumbo['arroba'] not in st.session_state["feedbacks_dados"]:
            col_fb1, col_fb2, _ = st.columns([1, 1, 2])
            with col_fb1:
                if st.button("👍 Sim, buscar parecidos", key=f"up_{chumbo['arroba']}_{contexto}"):
                    st.session_state["bons_exemplos"].append(chumbo.get('bio', ''))
                    st.session_state["feedbacks_dados"].append(chumbo['arroba'])
                    salvar_feedback_planilha(chumbo['arroba'], "Like", chumbo.get('bio', ''))
                    st.rerun()
            with col_fb2:
                if st.button("👎 Não, perfil ruim", key=f"down_{chumbo['arroba']}_{contexto}"):
                    st.session_state["maus_exemplos"].append(chumbo.get('bio', ''))
                    st.session_state["feedbacks_dados"].append(chumbo['arroba'])
                    salvar_feedback_planilha(chumbo['arroba'], "Dislike", chumbo.get('bio', ''))
                    st.rerun()
        else:
            st.success("✅ Feedback guardado no cérebro da IA!")

# ==========================================
# 🚀 FUNÇÃO DE PROCESSAMENTO BLINDADA
# ==========================================
def processar_lista_arrobas(lista_de_arrobas):
    st.session_state["leads_aprovados_tela"] = []
    st.session_state["leads_reprovados_tela"] = []
    
    barra = st.progress(0)
    for i, arroba in enumerate(lista_de_arrobas):
        barra.progress((i + 1) / len(lista_de_arrobas), text=f"A analisar {arroba} na IA...")
        
        st.session_state["blacklist_arrobas"].add(arroba)
        
        bio = buscar_bio_no_google(arroba, st.session_state["api_key_serper"])
        if bio and "Erro" not in bio and "Nenhuma" not in bio:
            avaliacao = analisar_e_gerar_script(arroba, bio, st.session_state["api_key_gemini"], seu_nome, anos_exp)
            
            if avaliacao.get("status") == "APROVADO":
                lead_aprovado = {
                    "arroba": arroba, "bio": bio, "script_1": avaliacao.get("script_1"), 
                    "motivo": avaliacao.get("motivo")
                }
                st.session_state["leads_aprovados_tela"].append(lead_aprovado)
                
                arrobas_salvos = [l["arroba"] for l in st.session_state["historico_leads"]]
                if arroba not in arrobas_salvos:
                    st.session_state["historico_leads"].insert(0, lead_aprovado) 
            else:
                st.session_state["leads_reprovados_tela"].append({"arroba": arroba, "motivo": avaliacao.get("motivo")})
        else:
            st.session_state["leads_reprovados_tela"].append({"arroba": arroba, "motivo": "Perfil fechado ou sem dados."})
        time.sleep(1.0)
    barra.empty()

# ==========================================
# 🖥️ RENDERIZAR ECRÃ ATUAL
# ==========================================
def renderizar_resultados_garimpo(contexto_render):
    if st.session_state["leads_aprovados_tela"]:
        st.divider()
        st.subheader(f"✅ {len(st.session_state['leads_aprovados_tela'])} Leads Aprovados")
        for chumbo in st.session_state["leads_aprovados_tela"]:
            desenhar_card_lead(chumbo, contexto=contexto_render)
            
    if st.session_state["leads_reprovados_tela"]:
        st.subheader(f"❌ {len(st.session_state['leads_reprovados_tela'])} Leads Descartados")
        for lixo in st.session_state["leads_reprovados_tela"]:
            st.write(f"- **{lixo['arroba']}**: {lixo['motivo']}")

# --- INTERFACE COM ABAS ---
aba_garimpo, aba_busca, aba_historico, aba_crm = st.tabs(["🔍 Garimpo", "📝 Colar @Arrobas", "📚 Histórico", "📊 Planilha CRM"])

with aba_garimpo:
    st.subheader("Encontrar e Qualificar Leads de forma automática")
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])
    with col1:
        nicho_alvo = st.text_input("Nicho / Profissão:", placeholder="Ex: Arquiteto")
    with col2:
        hashtag_alvo = st.text_input("Hashtag (Opcional):", placeholder="Ex: #decoracao")
    with col3:
        local_alvo = st.text_input("Localização (Opcional):", placeholder="Ex: São Paulo")
    with col4:
        qtd_busca = st.number_input("Qtd:", min_value=5, max_value=50, value=15, step=5)

    # 🛠️ FILTROS AVANÇADOS (Novo Módulo)
    with st.expander("🛠️ Filtros Avançados de Busca (Opcional)", expanded=False):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            termos_negativos = st.text_input("Palavras para EXCLUIR (separadas por vírgula):", placeholder="Ex: estudante, curso, fanpage")
        with col_f2:
            frase_exata = st.text_input("Frase EXATA na Bio do Instagram:", placeholder='Ex: Agende sua consulta')
        
    if st.button("🔍 Iniciar Nova Busca", type="primary", use_container_width=True):
        if not st.session_state["api_key_serper"] or not st.session_state["api_key_gemini"]:
            st.error("Preencha as duas API Keys no painel lateral!")
        elif not nicho_alvo and not hashtag_alvo:
            st.warning("Preencha o Nicho/Profissão ou uma Hashtag.")
        else:
            st.session_state["ultima_busca_nicho"] = nicho_alvo
            st.session_state["ultima_busca_hashtag"] = hashtag_alvo
            st.session_state["ultima_busca_local"] = local_alvo
            st.session_state["ultima_busca_negativos"] = termos_negativos
            st.session_state["ultima_busca_frase"] = frase_exata
            st.session_state["proxima_pagina"] = 1
            
            with st.spinner(f"A varrer a internet..."):
                arrobas, prox_pag = garimpar_perfis_google(
                    nicho_alvo, hashtag_alvo, local_alvo, termos_negativos, frase_exata,
                    qtd_busca, st.session_state["api_key_serper"], 1
                )
                st.session_state["proxima_pagina"] = prox_pag
                
            if arrobas:
                processar_lista_arrobas(arrobas)
            else:
                st.warning("Não foram encontrados novos perfis (ou os encontrados já constavam na sua Blacklist). Tente novos termos!")

    if st.session_state["ultima_busca_nicho"] or st.session_state["ultima_busca_hashtag"]:
        texto_busca = f"*{st.session_state['ultima_busca_nicho']}*" if st.session_state['ultima_busca_nicho'] else ""
        if st.session_state['ultima_busca_hashtag']:
            texto_busca += f" *{st.session_state['ultima_busca_hashtag']}*"
        if st.session_state['ultima_busca_local']:
            texto_busca += f" em *{st.session_state['ultima_busca_local']}*"
            
        st.markdown(f"**Continuar o garimpo:** {texto_busca}")
        
        if st.button("➕ Pesquisar Mais 10 Novos Leads", type="secondary", use_container_width=True):
            with st.spinner(f"A folhear o Google (Página {st.session_state['proxima_pagina']})..."):
                arrobas, prox_pag = garimpar_perfis_google(
                    st.session_state["ultima_busca_nicho"], 
                    st.session_state["ultima_busca_hashtag"],
                    st.session_state["ultima_busca_local"], 
                    st.session_state["ultima_busca_negativos"],
                    st.session_state["ultima_busca_frase"],
                    10, st.session_state["api_key_serper"], st.session_state["proxima_pagina"]
                )
                st.session_state["proxima_pagina"] = prox_pag
            if arrobas:
                processar_lista_arrobas(arrobas)
            else:
                st.warning("Fim dos resultados ou apenas perfis repetidos. Tente novos termos!")

    renderizar_resultados_garimpo("garimpo")

with aba_busca:
    st.subheader("Processar Lista Própria")
    lista_arrobas = st.text_area("Cole os @arrobas (um por linha):", height=150)
    if st.button("🚀 Processar Lote Manual", type="primary"):
        if lista_arrobas.strip():
            arrobas = [a.strip() for a in lista_arrobas.split("\n") if a.strip()]
            processar_lista_arrobas(arrobas)
    
    renderizar_resultados_garimpo("busca_manual")

with aba_historico:
    st.subheader("📚 Os seus Leads Qualificados")
    if not st.session_state["historico_leads"]:
        st.info("Nenhum lead qualificado ainda.")
    else:
        for chumbo in st.session_state["historico_leads"]:
            desenhar_card_lead(chumbo, contexto="historico")

with aba_crm:
    st.subheader("📊 Planilha CRM Integrada")
    components.iframe("https://docs.google.com/spreadsheets/d/1Ru4E7ArF3UKiPhkqjy0OkrCkdSKzcjHHchQm5v-836g/edit?rm=minimal", height=800, scrolling=True)

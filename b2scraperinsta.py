import streamlit as st
import requests
import json
import google.generativeai as genai
import time
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="Máquina de Qualificação em Massa", page_icon="⚡", layout="wide")

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
    NOME_ABA_PADRAO = "Página1"

# --- INICIALIZANDO MEMÓRIAS BLINDADAS ---
if "historico_leads" not in st.session_state:
    st.session_state["historico_leads"] = []
if "ultima_busca_nicho" not in st.session_state:
    st.session_state["ultima_busca_nicho"] = ""
if "ultima_busca_local" not in st.session_state:
    st.session_state["ultima_busca_local"] = ""
if "proxima_pagina" not in st.session_state:
    st.session_state["proxima_pagina"] = 1

# Memória para a tela não apagar (Problema 5)
if "leads_aprovados_tela" not in st.session_state:
    st.session_state["leads_aprovados_tela"] = []
if "leads_reprovados_tela" not in st.session_state:
    st.session_state["leads_reprovados_tela"] = []

# Blacklist para não repetir leads (Problema 4)
if "blacklist_arrobas" not in st.session_state:
    st.session_state["blacklist_arrobas"] = set()

# Memória de Treinamento da IA e CRM
if "bons_exemplos" not in st.session_state:
    st.session_state["bons_exemplos"] = []
if "maus_exemplos" not in st.session_state:
    st.session_state["maus_exemplos"] = []
if "feedbacks_dados" not in st.session_state:
    st.session_state["feedbacks_dados"] = [] 

# --- Layout do Cabeçalho ---
col_titulo, col_botoes = st.columns([3, 1])
with col_titulo:
    st.title("⚡ Máquina de Garimpo e Qualificação")
    st.markdown("Encontre perfis, qualifique com IA e mande para a aba certa do CRM com 1 clique.")
with col_botoes:
    st.write("") 
    st.write("")
    st.link_button("📊 Planilha de Controle", "https://docs.google.com/spreadsheets/d/1Ru4E7ArF3UKiPhkqjy0OkrCkdSKzcjHHchQm5v-836g/edit?gid=1121870777#gid=1121870777", use_container_width=True)
    st.link_button("💼 B2ScraperLinkedIn", "https://b2scraper.streamlit.app/", use_container_width=True)

# --- Configurações na Barra Lateral ---
with st.sidebar:
    st.header("⚙️ Configurações")
    
    if "api_key_serper" not in st.session_state:
        st.session_state["api_key_serper"] = CHAVE_SERPER_PADRAO
    if "api_key_gemini" not in st.session_state:
        st.session_state["api_key_gemini"] = CHAVE_GEMINI_PADRAO
    if "url_webhook" not in st.session_state:
        st.session_state["url_webhook"] = URL_WEBHOOK_PLANILHA
    if "nome_aba" not in st.session_state:
        st.session_state["nome_aba"] = NOME_ABA_PADRAO

    api_key_serper = st.text_input("API Key do Serper:", type="password", value=st.session_state["api_key_serper"])
    api_key_gemini = st.text_input("API Key do Google Gemini:", type="password", value=st.session_state["api_key_gemini"])
    
    st.divider()
    st.markdown("🎯 **Destino na Planilha (CRM):**")
    # PROBLEMA 1 e 2 RESOLVIDOS: O usuário escolhe a aba aqui e o software respeita.
    url_webhook = st.text_input("URL do Webhook:", type="password", value=st.session_state["url_webhook"])
    nome_aba = st.text_input("Nome exato da Aba:", value=st.session_state["nome_aba"], help="Ex: Página1, 27/03. Cuidado com espaços extras!")
    
    st.session_state["api_key_serper"] = api_key_serper
    st.session_state["api_key_gemini"] = api_key_gemini
    st.session_state["url_webhook"] = url_webhook
    st.session_state["nome_aba"] = nome_aba
    
    st.divider()
    st.markdown("👤 **Seu Perfil (BDR):**")
    seu_nome = st.text_input("Seu Nome:", value="Henrique Durant")
    anos_exp = st.text_input("Anos de Experiência:", value="5")

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

# --- MOTOR DE GARIMPO (Ignora Repetidos) ---
def garimpar_perfis_google(profissao, localizacao, qtd, api_serper, pagina_inicial=1):
    url = "https://google.serper.dev/search"
    query = f'site:instagram.com "{profissao}"'
    if localizacao:
        query += f' "{localizacao}"'
    
    arrobas_encontrados = []
    palavras_ignoradas = ['p', 'reel', 'reels', 'explore', 'tags', 'stories', 'tv', 'channel', 'about', 'legal', 'directory']
    
    paginas_necessarias = (qtd // 10) + 4 
    ultima_pagina_pesquisada = pagina_inicial
    
    barra_busca = st.progress(0, text="Buscando novos leads no Google...")
    
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
                        
                        # PROBLEMA 4 RESOLVIDO: Verifica se já vimos esse cara antes
                        if arroba_formatado not in st.session_state["blacklist_arrobas"] and arroba_formatado not in arrobas_encontrados:
                            arrobas_encontrados.append(arroba_formatado)
                        
                        if len(arrobas_encontrados) >= qtd:
                            break
                            
        except Exception as e:
            break
            
        time.sleep(0.5) 
        
    barra_busca.empty()
    return arrobas_encontrados[:qtd], ultima_pagina_pesquisada + 1

# --- CÉREBRO DA IA ---
def analisar_e_gerar_script(arroba, snippet_google, api_gemini, nome_bdr, exp_bdr):
    try:
        genai.configure(api_key=api_gemini)
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not modelos_disponiveis:
            return {"status": "ERRO", "motivo": "Sem acesso a IA."}
            
        modelo_escolhido = modelos_disponiveis[0]
        for nome in modelos_disponiveis:
            if 'flash' in nome:
                modelo_escolhido = nome
                
        modelo = genai.GenerativeModel(modelo_escolhido.replace("models/", ""))
        
        prompt = f"""
        Você atua como o Renê, um BDR de High-Ticket especialista em qualificação de leads.
        O seu ICP EXATO é: Dono de pequena/média empresa, Profissional liberal, Consultor/mentor, Médico/odontólogo, Advogado, Corretor/assessor, Gestor/comercial, Executivo, Engenheiro/arquiteto.

        CRITÉRIOS:
        1. Foto: Se amadora/inadequada (ex: sem camisa), REPROVAR.
        2. Seguidores: Ideal 2k a 50k. MAIS de 50k REPROVAR.
        3. Bio bagunçada ou Posicionamento fraco: APROVAR.
        4. Perfil Privado: Se "This account is private" ou "Conta privada", REPROVAR IMEDIATAMENTE.
        *Atenção*: Se não houver dados exatos para reprovar, APROVE.

        Resumo do Google para a conta {arroba}: "{snippet_google}"

        Sua tarefa: Descubra Nome, Área/Especialidade. Avalie se é ICP (APROVADO ou REPROVADO). Se APROVADO, gere 3 SCRIPTS.

        [SCRIPT INICIAL 1 - COM ESPECIALIDADE]
        Olá, [NOME]. Tudo bem?
        Espero que sim.
        Aqui é o {nome_bdr}, muito prazer. Eu trabalho há mais de {exp_bdr} anos ajudando empresários a serem percebidos como autoridade, conseguirem vender mais, cobrando melhor e com maior lucro.
        Me deparei com seu perfil e gostei muito do conteúdo que você gera sobre [ÁREA X], principalmente do seu foco em [ESPECIALIDADE].
        Vi que o seu perfil tem várias semelhanças com profissionais que atendo, mas também percebi alguns pontos que podem estar limitando a forma como o mercado te enxerga — e isso normalmente impacta diretamente no quanto você consegue cobrar e nas oportunidades que chegam até você.
        Posso compartilhar essas observações?

        [SCRIPT INICIAL 2 - SEM ESPECIALIDADE]
        Olá, [NOME]. Tudo bem?
        espero que sim.
        Aqui é o {nome_bdr}, muito prazer. Eu trabalho há mais de {exp_bdr} anos ajudando empresários a serem percebidos como autoridade, conseguirem vender mais, cobrando melhor e com maior lucro.
        Me deparei com seu perfil e gostei muito do conteúdo que você gera sobre [ÁREA X].
        Vi que o seu perfil tem várias semelhanças com profissionais que atendo, mas também percebi alguns pontos que podem estar limitando a forma como o mercado te enxerga — e isso normalmente impacta diretamente no quanto você consegue cobrar e nas oportunidades que chegam até você.
        Posso compartilhar essas observações?

        [SCRIPT DE 2 DIAS]
        Boa tarde, [NOME]. tudo bem? Espero que sim.
        Chegou a ver minha mensagem? O que me diz? 🙂

        [SCRIPT DE 4 DIAS]
        Boa tarde, [NOME]. Tudo certo por aí? Espero que sim.
        Estou retomando o contato contigo pois pelo pouco que acompanhei seu Instagram, ficou muito claro para mim que você é uma pessoa extremamente empenhada... Tenho diversas pessoas com um perfil semelhante ao seu tendo grandes transformações... gostaria de saber se você tem algum interesse em entender melhor ou se posso seguir adiante. Abraços.

        Retorne APENAS um objeto JSON válido (sem markdown):
        "status": "APROVADO" ou "REPROVADO", "motivo": "justificativa curta", "script_1": "texto ou vazio", "script_2": "texto ou vazio", "script_3": "texto ou vazio"
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
def desenhar_card_lead(chumbo):
    with st.expander(f"🔥 {chumbo['arroba']} - ICP Aprovado", expanded=False):
        username_limpo = chumbo['arroba'].replace('@', '').strip()
        username_limpo = re.sub(r'(https?://)?(www\.)?instagram\.com/', '', username_limpo)
        username_limpo = username_limpo.replace('/', '') 
        link_ig = f"https://www.instagram.com/{username_limpo}/"
        
        col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])
        with col1:
            st.caption(f"**Motivo:** {chumbo['motivo']}")
        with col2:
            st.code(username_limpo, language=None)
        with col3:
            st.link_button("👉 Abrir Insta", link_ig, use_container_width=True, type="primary")
        with col4:
            dados_planilha = chumbo.copy()
            dados_planilha["link_ig"] = link_ig
            dados_planilha["sheet_name"] = st.session_state["nome_aba"]
            
            # Botão de Enviar CRM blindado (não apaga a tela)
            btn_key = f"crm_{chumbo['arroba']}"
            if btn_key not in st.session_state:
                st.session_state[btn_key] = False
                
            if not st.session_state[btn_key]:
                if st.button("✅ Enviar CRM", key=f"btn_{btn_key}", use_container_width=True):
                    if enviar_lead_para_planilha(dados_planilha):
                        st.session_state[btn_key] = True
                        st.rerun() # Atualiza pra mostrar que enviou, mas como a tela tá salva, não apaga!
            else:
                st.success("✅ Enviado!")
            
        st.divider()
        st.code(chumbo.get('script_1', ''), language="markdown")
        st.code(chumbo.get('script_2', ''), language="markdown")
        st.code(chumbo.get('script_3', ''), language="markdown")

# ==========================================
# 🚀 FUNÇÃO DE PROCESSAMENTO BLINDADA
# ==========================================
def processar_lista_arrobas(lista_de_arrobas):
    st.session_state["leads_aprovados_tela"] = []
    st.session_state["leads_reprovados_tela"] = []
    
    barra = st.progress(0)
    for i, arroba in enumerate(lista_de_arrobas):
        barra.progress((i + 1) / len(lista_de_arrobas), text=f"Analisando {arroba} na IA...")
        
        # Coloca o lead na Blacklist para nunca mais pesquisar ele hoje
        st.session_state["blacklist_arrobas"].add(arroba)
        
        bio = buscar_bio_no_google(arroba, st.session_state["api_key_serper"])
        if bio and "Erro" not in bio and "Nenhuma" not in bio:
            avaliacao = analisar_e_gerar_script(arroba, bio, st.session_state["api_key_gemini"], seu_nome, anos_exp)
            
            if avaliacao.get("status") == "APROVADO":
                lead_aprovado = {
                    "arroba": arroba, "bio": bio, "script_1": avaliacao.get("script_1"), 
                    "script_2": avaliacao.get("script_2"), "script_3": avaliacao.get("script_3"), 
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
# 🖥️ RENDERIZAR TELA ATUAL (Evita apagar)
# ==========================================
def renderizar_resultados_garimpo():
    if st.session_state["leads_aprovados_tela"]:
        st.divider()
        st.subheader(f"✅ {len(st.session_state['leads_aprovados_tela'])} Leads Aprovados")
        for chumbo in st.session_state["leads_aprovados_tela"]:
            desenhar_card_lead(chumbo)
            
    if st.session_state["leads_reprovados_tela"]:
        st.subheader(f"❌ {len(st.session_state['leads_reprovados_tela'])} Leads Descartados")
        for lixo in st.session_state["leads_reprovados_tela"]:
            st.write(f"- **{lixo['arroba']}**: {lixo['motivo']}")

# --- INTERFACE COM ABAS ---
aba_garimpo, aba_busca, aba_historico, aba_crm = st.tabs(["🔍 Garimpo", "📝 Colar @Arrobas", "📚 Histórico", "📊 Planilha CRM"])

with aba_garimpo:
    st.subheader("Encontrar e Qualificar Leads de forma automática")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        nicho_alvo = st.text_input("Nicho / Profissão:", placeholder="Ex: Advogado Tributarista")
    with col2:
        local_alvo = st.text_input("Localização (Opcional):", placeholder="Ex: São Paulo")
    with col3:
        qtd_busca = st.number_input("Qtd. Máxima:", min_value=5, max_value=50, value=15, step=5)
        
    if st.button("🔍 Iniciar Nova Busca", type="primary", use_container_width=True):
        if not st.session_state["api_key_serper"] or not st.session_state["api_key_gemini"]:
            st.error("Preencha as duas API Keys na barra lateral!")
        elif not nicho_alvo:
            st.warning("Preencha o Nicho/Profissão.")
        else:
            st.session_state["ultima_busca_nicho"] = nicho_alvo
            st.session_state["ultima_busca_local"] = local_alvo
            st.session_state["proxima_pagina"] = 1
            
            with st.spinner(f"Varrendo a internet atrás de {nicho_alvo}..."):
                arrobas, prox_pag = garimpar_perfis_google(nicho_alvo, local_alvo, qtd_busca, st.session_state["api_key_serper"], 1)
                st.session_state["proxima_pagina"] = prox_pag
                
            if arrobas:
                processar_lista_arrobas(arrobas)
            else:
                st.warning("Não foram encontrados novos perfis com estes termos (os repetidos foram ignorados).")

    if st.session_state["ultima_busca_nicho"]:
        st.markdown(f"**Continuar o garimpo:** *{st.session_state['ultima_busca_nicho']}* em *{st.session_state['ultima_busca_local']}*")
        if st.button("➕ Pesquisar Mais 10 Novos Leads", type="secondary", use_container_width=True):
            with st.spinner(f"Folheando o Google (Página {st.session_state['proxima_pagina']})..."):
                arrobas, prox_pag = garimpar_perfis_google(
                    st.session_state["ultima_busca_nicho"], st.session_state["ultima_busca_local"], 
                    10, st.session_state["api_key_serper"], st.session_state["proxima_pagina"]
                )
                st.session_state["proxima_pagina"] = prox_pag
            if arrobas:
                processar_lista_arrobas(arrobas)
            else:
                st.warning("Fim dos resultados ou só vieram repetidos. Tente outro nicho!")

    # Renderiza os leads na tela SEMPRE (assim eles não somem no Rerun do botão)
    renderizar_resultados_garimpo()

with aba_busca:
    st.subheader("Processar Lista Própria")
    lista_arrobas = st.text_area("Cole os @arrobas (um por linha):", height=150)
    if st.button("🚀 Processar Lote Manual", type="primary"):
        if lista_arrobas.strip():
            arrobas = [a.strip() for a in lista_arrobas.split("\n") if a.strip()]
            processar_lista_arrobas(arrobas)
    renderizar_resultados_garimpo()

with aba_historico:
    st.subheader("📚 Seus Leads Qualificados")
    if not st.session_state["historico_leads"]:
        st.info("Nenhum lead qualificado ainda.")
    else:
        for chumbo in st.session_state["historico_leads"]:
            desenhar_card_lead(chumbo)

with aba_crm:
    st.subheader("📊 Planilha CRM Integrada")
    components.iframe("https://docs.google.com/spreadsheets/d/1Ru4E7ArF3UKiPhkqjy0OkrCkdSKzcjHHchQm5v-836g/edit?rm=minimal", height=800, scrolling=True)

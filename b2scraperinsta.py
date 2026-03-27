import streamlit as st
import requests
import json
import google.generativeai as genai
import time
import re

st.set_page_config(page_title="Máquina de Qualificação em Massa", page_icon="⚡", layout="wide")

# ==========================================
# 🔑 PUXANDO CHAVES COM SEGURANÇA (SECRETS)
# ==========================================
try:
    CHAVE_SERPER_PADRAO = st.secrets["CHAVE_SERPER"]
    CHAVE_GEMINI_PADRAO = st.secrets["CHAVE_GEMINI"]
except Exception:
    CHAVE_SERPER_PADRAO = ""
    CHAVE_GEMINI_PADRAO = ""

# --- INICIALIZANDO O HISTÓRICO NA MEMÓRIA ---
if "historico_leads" not in st.session_state:
    st.session_state["historico_leads"] = []

# --- Layout do Cabeçalho com os botões ---
col_titulo, col_botoes = st.columns([3, 1])
with col_titulo:
    st.title("⚡ Máquina de Garimpo e Qualificação")
    st.markdown("Encontre perfis automaticamente pelo Google, qualifique o ICP com Inteligência Artificial e gere os scripts de vendas prontos a copiar.")
with col_botoes:
    st.write("") 
    st.write("")
    st.link_button("📊 Planilha de Controlo", "https://docs.google.com/spreadsheets/d/1PZimYKWupEv3x_pR9AVnl_mquBuUFfX0gWPO9iCpGFQ/edit?gid=1396779725#gid=1396779725", use_container_width=True)
    st.link_button("💼 B2ScraperLinkedIn", "https://b2scraper.streamlit.app/", use_container_width=True)
    st.link_button("🕵️ Dossiê ABM", "https://b2scraperweb.streamlit.app/", use_container_width=True)

# --- Configurações na Barra Lateral ---
with st.sidebar:
    st.header("⚙️ Chaves de Acesso")
    
    if "api_key_serper" not in st.session_state:
        st.session_state["api_key_serper"] = CHAVE_SERPER_PADRAO
    if "api_key_gemini" not in st.session_state:
        st.session_state["api_key_gemini"] = CHAVE_GEMINI_PADRAO

    api_key_serper = st.text_input("API Key do Serper:", type="password", value=st.session_state["api_key_serper"])
    api_key_gemini = st.text_input("API Key do Google Gemini:", type="password", value=st.session_state["api_key_gemini"])
    
    st.session_state["api_key_serper"] = api_key_serper
    st.session_state["api_key_gemini"] = api_key_gemini
    
    st.divider()
    st.markdown("**O Seu Perfil (BDR):**")
    seu_nome = st.text_input("O Seu Nome:", value="Henrique Durant")
    anos_exp = st.text_input("Anos de Experiência:", value="5")

# --- MOTOR DE GARIMPO (GOOGLE HACK MELHORADO) ---
def garimpar_perfis_google(profissao, localizacao, qtd, api_serper):
    url = "https://google.serper.dev/search"
    
    # Busca simplificada para não bugar o Google. 
    query = f'site:instagram.com "{profissao}"'
    if localizacao:
        query += f' "{localizacao}"'
    
    payload = json.dumps({"q": query, "num": 100}) # Pede 100 pra garantir margem
    headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
    
    try:
        res = requests.post(url, headers=headers, data=payload)
        
        # Se a API der erro (ex: falta de crédito), vai mostrar na tela agora!
        if not res.ok:
            st.error(f"Erro na API do Serper: {res.text}")
            return []
            
        dados = res.json()
        arrobas_encontrados = []
        
        # Palavras reservadas do Instagram que não são perfis
        palavras_ignoradas = ['p', 'reel', 'reels', 'explore', 'tags', 'stories', 'tv', 'channel', 'about', 'legal', 'directory']
        
        for item in dados.get("organic", []):
            link = item.get("link", "")
            # Extrair o nome de utilizador do link
            match = re.search(r'instagram\.com/([^/?]+)', link)
            if match:
                username = match.group(1).strip()
                # O filtro agora é feito no Python, mais seguro e eficiente
                if username.lower() not in palavras_ignoradas:
                    arroba_formatado = f"@{username}"
                    if arroba_formatado not in arrobas_encontrados:
                        arrobas_encontrados.append(arroba_formatado)
                    
                    if len(arrobas_encontrados) >= qtd:
                        break
                        
        return arrobas_encontrados
    except Exception as e:
        st.error(f"Erro interno ao buscar perfis: {str(e)}")
        return []

# --- O CÉREBRO DA IA ---
def analisar_e_gerar_script(arroba, snippet_google, api_gemini, nome_bdr, exp_bdr):
    try:
        genai.configure(api_key=api_gemini)
        
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not modelos_disponiveis:
            return {"status": "ERRO", "motivo": "A sua chave não tem acesso a nenhum modelo de geração de texto.", "script_1": "", "script_2": "", "script_3": ""}
            
        modelo_escolhido = modelos_disponiveis[0]
        for nome in modelos_disponiveis:
            if 'flash' in nome or 'pro' in nome:
                modelo_escolhido = nome
                break
                
        nome_limpo = modelo_escolhido.replace("models/", "")
        modelo = genai.GenerativeModel(nome_limpo)
        
        prompt = f"""
        Você atua como o Renê, um BDR de High-Ticket especialista em qualificação de leads. A empresa vende a mentoria "Código do Valor".
        A mentoria custa R$40.000,00 e dura 1 ano (podendo parcelar em até 12x), ou R$25.000,00 por 6 meses.

        O seu ICP (Público-Alvo) EXATO é:
        - Dono de pequena/média empresa
        - Profissional liberal
        - Consultor/mentor
        - Médico/odontólogo
        - Advogado
        - Corretor/assessor
        - Gestor/comercial
        - Executivo que empreende lateralmente
        - Engenheiro/arquiteto

        CRITÉRIOS DE AVALIAÇÃO (Aprovação/Reprovação):
        1. Foto de perfil: Se tentar ser profissional, OK. Se estiver claro no texto que é amadora/inadequada (ex: sem camisa), REPROVAR.
        2. Selo Verificado: Diferencial, mas não é eliminatório se não tiver.
        3. Seguidores: Ideal 2k a 50k. Menos que 2k é OK. MAIS de 50k REPROVAR (já deve ter mentoria).
        4. Bio bagunçada: APROVAR (ótimo para nós, significa que podemos ajudar).
        5. Posicionamento ruim/fraco: APROVAR (ótimo para nós, é o que resolvemos).
        *Atenção*: Como analisa apenas textos extraídos do Google, se não houver menção sobre a foto ou número exato de seguidores, assuma que está OK e NÃO reprove por falta de dados. Só reprove se a informação lida deixar claro a violação das regras.

        Aqui está o resumo que o Google obteve do Instagram da conta {arroba}:
        "{snippet_google}"

        A sua tarefa:
        1. Descubra o Nome da pessoa (primeiro nome).
        2. Descubra a Área (ex: Odontologia) e Especialidade.
        3. Avalie se é ICP (APROVADO ou REPROVADO) com base nas regras acima e se tem potencial para pagar R$25k-R$40k.
        4. Se APROVADO, gere OS 3 SCRIPTS EXATOS abaixo. 

        Se TIVER especialidade clara, use o SCRIPT INICIAL 1. Se NÃO TIVER, use o SCRIPT INICIAL 2.
        Substitua apenas os colchetes [NOME], [ÁREA X] e [ESPECIALIDADE]. Troque [NOME DO BDR] por {nome_bdr} e {exp_bdr} pelos valores passados. NÃO MUDE MAIS NADA NO TEXTO.

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
        Boa tarde, [NOME].
        tudo bem?
        Espero que sim.

        Chegou a ver minha mensagem?
        O que me diz? 🙂

        [SCRIPT DE 4 DIAS]
        Boa tarde, [NOME].
        Tudo certo por aí?
        Espero que sim.
        Estou retomando o contato contigo pois pelo pouco que acompanhei seu Instagram, ficou muito claro para mim que você é uma pessoa extremamente empenhada no que busca fazer e muito comprometida com o seu negócio, sua autoridade e imagem pessoal.
        Tenho diversas pessoas com um perfil semelhante ao seu, tendo grandes transformações com o meu método para ser percebido como autoridade e atrair clientes qualificados.
        Por todos esses motivos, acredito que o projeto possa ser muito agregador para ti, porém vem sendo um tanto quanto difícil de nos comunicarmos, então eu gostaria de saber se você tem algum interesse em entender melhor ou se realmente posso seguir adiante e falar com novas pessoas.
        Abraços.

        Retorne APENAS um objeto JSON válido (sem marcação markdown, apenas o JSON puro) com estas exatas chaves:
        "status": "APROVADO" ou "REPROVADO",
        "motivo": "A justificativa curta de aprovação ou reprovação baseada nas suas regras",
        "script_1": "Insira aqui O SCRIPT INICIAL (1 ou 2) gerado. Deixe vazio se reprovado.",
        "script_2": "Insira aqui O SCRIPT DE 2 DIAS gerado. Deixe vazio se reprovado.",
        "script_3": "Insira aqui O SCRIPT DE 4 DIAS gerado. Deixe vazio se reprovado."
        """
        
        resposta = modelo.generate_content(prompt)
        texto_json = resposta.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_json)
        
    except Exception as e:
        return {"status": "ERRO", "motivo": f"Falha na IA: {e}", "script_1": "", "script_2": "", "script_3": ""}

def buscar_bio_no_google(arroba, api_serper):
    url = "https://google.serper.dev/search"
    query = f'site:instagram.com "{arroba}"'
    payload = json.dumps({"q": query, "num": 1})
    headers = {'X-API-KEY': api_serper, 'Content-Type': 'application/json'}
    
    try:
        res = requests.post(url, headers=headers, data=payload)
        res.raise_for_status()
        dados = res.json()
        if "organic" in dados and len(dados["organic"]) > 0:
            return dados["organic"][0].get("snippet", "") + " " + dados["organic"][0].get("title", "")
        return "Nenhuma informação encontrada no Google."
    except:
        return "Erro ao buscar no Google."

# ==========================================
# 🎨 DESIGN DA CAIXA DO LEAD (OTIMIZADO)
# ==========================================
def desenhar_card_lead(chumbo):
    with st.expander(f"🔥 {chumbo['arroba']} - ICP Aprovado"):
        username_limpo = chumbo['arroba'].replace('@', '').strip()
        username_limpo = re.sub(r'(https?://)?(www\.)?instagram\.com/', '', username_limpo)
        username_limpo = username_limpo.replace('/', '') 
        link_ig = f"https://www.instagram.com/{username_limpo}/"
        
        col_motivo, col_botao = st.columns([3, 1])
        with col_motivo:
            st.caption(f"**Porquê passou:** {chumbo['motivo']}")
        with col_botao:
            st.link_button("👉 Abrir Instagram", link_ig, use_container_width=True, type="primary")
            
        st.divider()
        
        st.markdown("**1️⃣ Mensagem Inicial (Diagnóstico)**")
        st.code(chumbo.get('script_1', ''), language="markdown")
        
        st.markdown("**2️⃣ Cobrança (2 Dias)**")
        st.code(chumbo.get('script_2', ''), language="markdown")
        
        st.markdown("**3️⃣ Xeque-Mate (4 Dias)**")
        st.code(chumbo.get('script_3', ''), language="markdown")

# ==========================================
# 🚀 FUNÇÃO PRINCIPAL DE PROCESSAMENTO
# ==========================================
def processar_lista_arrobas(lista_de_arrobas):
    st.info(f"A processar {len(lista_de_arrobas)} perfis. Isto pode demorar alguns segundos...")
    
    barra = st.progress(0)
    resultados_aprovados = []
    resultados_reprovados = []
    
    for i, arroba in enumerate(lista_de_arrobas):
        barra.progress((i + 1) / len(lista_de_arrobas), text=f"A analisar {arroba}...")
        
        bio = buscar_bio_no_google(arroba, api_key_serper)
        
        if bio and "Erro" not in bio and "Nenhuma" not in bio:
            avaliacao = analisar_e_gerar_script(arroba, bio, api_key_gemini, seu_nome, anos_exp)
            
            if avaliacao.get("status") == "APROVADO":
                lead_aprovado = {
                    "arroba": arroba, 
                    "script_1": avaliacao.get("script_1"), 
                    "script_2": avaliacao.get("script_2"), 
                    "script_3": avaliacao.get("script_3"), 
                    "motivo": avaliacao.get("motivo")
                }
                resultados_aprovados.append(lead_aprovado)
                
                # Guardar no Histórico
                arrobas_salvos = [l["arroba"] for l in st.session_state["historico_leads"]]
                if arroba not in arrobas_salvos:
                    st.session_state["historico_leads"].insert(0, lead_aprovado) 
                    
            else:
                resultados_reprovados.append({"arroba": arroba, "motivo": avaliacao.get("motivo")})
        else:
            resultados_reprovados.append({"arroba": arroba, "motivo": "Perfil fechado ou não indexado no Google."})
        
        time.sleep(1.5)
    
    barra.empty()
    st.divider()
    
    st.subheader(f"✅ {len(resultados_aprovados)} Leads Aprovados (ICP Confirmado)")
    for chumbo in resultados_aprovados:
        desenhar_card_lead(chumbo)
    
    if resultados_reprovados:
        st.subheader(f"❌ {len(resultados_reprovados)} Leads Descartados")
        for lixo in resultados_reprovados:
            st.write(f"- **{lixo['arroba']}**: {lixo['motivo']}")


# --- INTERFACE COM ABAS ---
aba_garimpo, aba_busca, aba_historico = st.tabs(["🔍 Garimpo Automático", "📝 Colar @Arrobas Manualmente", "📚 Histórico de Leads Salvos"])

with aba_garimpo:
    st.subheader("Encontrar e Qualificar Leads de forma automática")
    st.markdown("Insira o nicho e deixe o robô varrer o Google para encontrar e qualificar os potenciais clientes.")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        nicho_alvo = st.text_input("Nicho / Profissão:", placeholder="Ex: Advogado Tributarista")
    with col2:
        local_alvo = st.text_input("Localização (Opcional):", placeholder="Ex: São Paulo")
    with col3:
        qtd_busca = st.number_input("Qtd. Máxima:", min_value=5, max_value=50, value=15, step=5)
        
    if st.button("🔍 Garimpar e Qualificar", type="primary", use_container_width=True):
        if not api_key_serper or not api_key_gemini:
            st.error("Preencha as duas API Keys na barra lateral!")
        elif not nicho_alvo:
            st.warning("Preencha o Nicho/Profissão para o robô saber quem procurar.")
        else:
            with st.spinner(f"A varrer a internet à procura de {nicho_alvo}..."):
                arrobas_encontrados = garimpar_perfis_google(nicho_alvo, local_alvo, qtd_busca, api_key_serper)
                
            if not arrobas_encontrados:
                st.warning("Não foram encontrados perfis suficientes com estes termos. Tente ser mais genérico.")
            else:
                st.success(f"Foram capturados {len(arrobas_encontrados)} perfis brutos! A iniciar qualificação IA...")
                processar_lista_arrobas(arrobas_encontrados)

with aba_busca:
    st.subheader("Processar Lista Própria")
    lista_arrobas = st.text_area("Cole os @arrobas do Instagram (um por linha):", placeholder="@dr.joaocirurgiao\n@marcos.adv\n@clinica.estetica...", height=150)

    if st.button("🚀 Processar Lote Manual", type="primary"):
        if not api_key_serper or not api_key_gemini:
            st.error("Preencha as duas API Keys na barra lateral!")
        elif not lista_arrobas.strip():
            st.warning("Cole pelo menos um @arroba.")
        else:
            arrobas = [a.strip() for a in lista_arrobas.split("\n") if a.strip()]
            processar_lista_arrobas(arrobas)

with aba_historico:
    st.subheader("📚 Os Seus Leads Qualificados")
    st.markdown("Aqui ficam guardados os leads que já aprovou. Volte aqui para copiar as mensagens de **Follow-up** (2 ou 4 dias). *Eles desaparecerão se fechar a aba do navegador.*")
    
    if not st.session_state["historico_leads"]:
        st.info("Nenhum lead qualificado ainda. Volte às abas anteriores e processe a sua primeira lista!")
    else:
        for chumbo in st.session_state["historico_leads"]:
            desenhar_card_lead(chumbo)

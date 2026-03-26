import streamlit as st
import requests
import json
import google.generativeai as genai
import time

st.set_page_config(page_title="Máquina de Qualificação em Massa", page_icon="⚡", layout="wide")

# ==========================================
# 🔑 PUXANDO CHAVES COM SEGURANÇA (SECRETS)
# ==========================================
# Tenta pegar do Streamlit Secrets (nuvem). Se der erro, deixa vazio.
try:
    CHAVE_SERPER_PADRAO = st.secrets["CHAVE_SERPER"]
    CHAVE_GEMINI_PADRAO = st.secrets["CHAVE_GEMINI"]
except Exception:
    CHAVE_SERPER_PADRAO = ""
    CHAVE_GEMINI_PADRAO = ""

# --- Layout do Cabeçalho com o botão de Link Externo ---
col_titulo, col_botoes = st.columns([4, 1])
with col_titulo:
    st.title("⚡ Qualificador e Gerador de Scripts em Massa")
    st.markdown("Cole uma lista de @arrobas do Instagram. O sistema puxa os dados via Google, a IA qualifica o ICP e já cospe os textos prontos para copiar e colar.")
with col_botoes:
    st.write("") 
    st.write("")
    st.link_button("💼 Ir para B2ScraperLinkedIn", "https://b2scraper.streamlit.app/", use_container_width=True)


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
    st.markdown("**Seu Perfil (BDR):**")
    seu_nome = st.text_input("Seu Nome:", value="Henrique Durant")
    anos_exp = st.text_input("Anos de Experiência:", value="5")

# --- O CÉREBRO DA IA ---
def analisar_e_gerar_script(arroba, snippet_google, api_gemini, nome_bdr, exp_bdr):
    try:
        genai.configure(api_key=api_gemini)
        
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        if not modelos_disponiveis:
            return {"status": "ERRO", "motivo": "Sua chave não tem acesso a nenhum modelo de geração de texto.", "script": ""}
            
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
        *Atenção*: Como você analisa apenas textos extraídos do Google, se não houver menção sobre a foto ou número exato de seguidores, assuma que está OK e NÃO reprove por falta de dados. Só reprove se a informação lida deixar claro a violação das regras.

        Aqui está o resumo que o Google pegou do Instagram da conta {arroba}:
        "{snippet_google}"

        Sua tarefa:
        1. Descubra o Nome da pessoa (primeiro nome).
        2. Descubra a Área (ex: Odontologia) e Especialidade.
        3. Avalie se é ICP (APROVADO ou REPROVADO) com base nas regras acima e se ele tem potencial de pagar R$25k-R$40k.
        4. Se APROVADO, gere OS 3 SCRIPTS EXATOS abaixo. 

        Se TIVER especialidade clara, use o SCRIPT INICIAL 1. Se NÃO TIVER, use o SCRIPT INICIAL 2.
        Substitua apenas os colchetes [NOME], [ÁREA X] e [ESPECIALIDADE]. Troque {nome_bdr} e {exp_bdr} pelos valores passados. NÃO MUDE MAIS NADA NO TEXTO.

        [SCRIPT INICIAL 1 - COM ESPECIALIDADE]
        Olá, [NOME]. Tudo bem?
        Espero que sim.

        Aqui é o {nome_bdr}, muito prazer. Eu trabalho há mais de {exp_bdr} anos ajudando empresários a serem percebidos como autoridade, conseguirem vender mais, cobrando melhor e com maior lucro.

        Me deparei com seu perfil e gostei muito do conteúdo que você gera sobre [ÁREA X], mainly do seu foco em [ESPECIALIDADE].

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
        "script": "Insira aqui TODOS OS 3 SCRIPTS GERADOS (Inicial, 2 Dias e 4 Dias), separados por uma quebra de linha visual (Ex: --- MENSAGEM INICIAL --- ... --- APÓS 2 DIAS --- etc), para que o usuário possa copiar tudo de uma vez. Deixe vazio se reprovado."
        """
        
        resposta = modelo.generate_content(prompt)
        texto_json = resposta.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_json)
        
    except Exception as e:
        return {"status": "ERRO", "motivo": f"Falha na IA: {e}", "script": ""}

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

# --- INTERFACE DE AÇÃO ---
lista_arrobas = st.text_area("Cole os @arrobas do Instagram (um por linha):", placeholder="@dr.joaocirurgiao\n@marcos.adv\n@clinica.estetica...", height=150)

if st.button("🚀 Processar e Qualificar Lote", type="primary"):
    if not api_key_serper or not api_key_gemini:
        st.error("Preencha as duas API Keys na barra lateral (ou configure os Secrets)!")
    elif not lista_arrobas.strip():
        st.warning("Cole pelo menos um @arroba.")
    else:
        arrobas = [a.strip() for a in lista_arrobas.split("\n") if a.strip()]
        
        st.info(f"Processando {len(arrobas)} perfis. Isso pode levar alguns segundos...")
        
        barra = st.progress(0)
        resultados_aprovados = []
        resultados_reprovados = []
        
        for i, arroba in enumerate(arrobas):
            barra.progress((i + 1) / len(arrobas), text=f"Analisando {arroba}...")
            
            bio = buscar_bio_no_google(arroba, api_key_serper)
            
            if bio and "Erro" not in bio and "Nenhuma" not in bio:
                avaliacao = analisar_e_gerar_script(arroba, bio, api_key_gemini, seu_nome, anos_exp)
                
                if avaliacao.get("status") == "APROVADO":
                    resultados_aprovados.append({"arroba": arroba, "script": avaliacao.get("script"), "motivo": avaliacao.get("motivo")})
                else:
                    resultados_reprovados.append({"arroba": arroba, "motivo": avaliacao.get("motivo")})
            else:
                resultados_reprovados.append({"arroba": arroba, "motivo": "Perfil fechado ou não indexado no Google."})
            
            time.sleep(1.5)
        
        barra.empty()
        st.divider()
        
        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.subheader(f"✅ {len(resultados_aprovados)} Leads Aprovados (ICP Confirmado)")
        
        for chumbo in resultados_aprovados:
            with st.expander(f"🔥 {chumbo['arroba']} - Clique para enviar"):
                st.caption(f"Por que foi aprovado: {chumbo['motivo']}")
                st.code(chumbo['script'], language="markdown")
                
                link_ig = f"https://ig.me/m/{chumbo['arroba'].replace('@', '')}"
                st.markdown(f"[👉 Abrir Direct do **{chumbo['arroba']}** no Instagram]({link_ig})")
        
        if resultados_reprovados:
            st.subheader(f"❌ {len(resultados_reprovados)} Leads Descartados (Tempo economizado!)")
            for lixo in resultados_reprovados:
                st.write(f"- **{lixo['arroba']}**: {lixo['motivo']}")

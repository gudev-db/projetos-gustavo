import streamlit as st
import datetime
from pymongo import MongoClient
from bson import ObjectId
import hashlib

# Configuração inicial
st.set_page_config(
    layout="wide",
    page_title="Sistema de Acompanhamento de Projetos",
    page_icon="📊"
)

# --- Sistema de Autenticação ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Dados de usuário hardcoded
users = {
    "admin": make_hashes("admin123"),  # admin/admin123
    "user": make_hashes("user123")     # user/user123
}

def login():
    """Formulário de login"""
    st.title("🔐 Sistema de Acompanhamento de Projetos")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if username in users and check_hashes(password, users[username]):
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.user_role = "admin" if username == "admin" else "user"
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# Verificar se o usuário está logado
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# --- CONEXÃO MONGODB (APÓS LOGIN) ---
# Só conecta ao MongoDB depois que o usuário fez login
try:
    client = MongoClient("mongodb+srv://gustavoromao3345:RqWFPNOJQfInAW1N@cluster0.5iilj.mongodb.net/auto_doc?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE&tlsAllowInvalidCertificates=true")
    db = client['projetos_app']
    collection_projetos = db['projetos']
    collection_comentarios = db['comentarios']
    
    # Testar conexão
    client.admin.command('ping')
    st.sidebar.success("✅ Conectado ao MongoDB")
    
except Exception as e:
    st.error(f"❌ Erro na conexão com MongoDB: {e}")
    st.stop()

# --- Funções para Projetos ---
def criar_projeto(nome, descricao, responsavel, prazo):
    """Cria um novo projeto no MongoDB"""
    projeto = {
        "nome": nome,
        "descricao": descricao,
        "responsavel": responsavel,
        "prazo": prazo,
        "status": "Em andamento",
        "proxima_acao": "admin" if st.session_state.user_role == "admin" else "user",
        "data_criacao": datetime.datetime.now(),
        "criado_por": st.session_state.user,
        "ativo": True
    }
    result = collection_projetos.insert_one(projeto)
    return result.inserted_id

def listar_projetos():
    """Retorna todos os projetos ativos"""
    return list(collection_projetos.find({"ativo": True}).sort("data_criacao", -1))

def obter_projeto(projeto_id):
    """Obtém um projeto específico pelo ID"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    return collection_projetos.find_one({"_id": projeto_id})

def atualizar_projeto(projeto_id, dados_atualizacao):
    """Atualiza um projeto existente"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    dados_atualizacao["data_atualizacao"] = datetime.datetime.now()
    return collection_projetos.update_one(
        {"_id": projeto_id},
        {"$set": dados_atualizacao}
    )

def alternar_proxima_acao(projeto_id):
    """Alterna entre admin e user para próxima ação"""
    projeto = obter_projeto(projeto_id)
    if projeto:
        nova_acao = "user" if projeto["proxima_acao"] == "admin" else "admin"
        atualizar_projeto(projeto_id, {"proxima_acao": nova_acao})
        return nova_acao
    return None

def desativar_projeto(projeto_id):
    """Desativa um projeto (soft delete)"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    return collection_projetos.update_one(
        {"_id": projeto_id},
        {"$set": {"ativo": False, "data_desativacao": datetime.datetime.now()}}
    )

# --- Funções para Comentários ---
def adicionar_comentario(projeto_id, texto, autor):
    """Adiciona um comentário a um projeto"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    comentario = {
        "projeto_id": projeto_id,
        "texto": texto,
        "autor": autor,
        "data_criacao": datetime.datetime.now(),
        "ativo": True
    }
    result = collection_comentarios.insert_one(comentario)
    
    # Atualiza a próxima ação após comentário do user
    if autor == "user":
        alternar_proxima_acao(projeto_id)
    
    return result.inserted_id

def obter_comentarios(projeto_id):
    """Obtém todos os comentários de um projeto"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    return list(collection_comentarios.find(
        {"projeto_id": projeto_id, "ativo": True}
    ).sort("data_criacao", 1))

# --- Interface Principal ---
st.sidebar.title(f"👋 Bem-vindo, {st.session_state.user}!")
st.sidebar.write(f"**Função:** {st.session_state.user_role}")

# Botão de logout na sidebar
if st.sidebar.button("🚪 Sair"):
    for key in ["logged_in", "user", "user_role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.title("📊 Sistema de Acompanhamento de Projetos")

# Menu de abas
if st.session_state.user_role == "admin":
    tab_projetos, tab_criar, tab_dashboard = st.tabs([
        "📋 Meus Projetos", 
        "➕ Criar Projeto", 
        "📈 Dashboard"
    ])
else:
    tab_projetos, tab_dashboard = st.tabs([
        "📋 Projetos", 
        "📈 Dashboard"
    ])

with tab_projetos:
    st.header("📋 Lista de Projetos")
    
    projetos = listar_projetos()
    if projetos:
        for projeto in projetos:
            with st.expander(f"**{projeto['nome']}** - {projeto['status']} - Próxima ação: {projeto['proxima_acao']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Descrição:** {projeto['descricao']}")
                    st.write(f"**Responsável:** {projeto['responsavel']}")
                    st.write(f"**Prazo:** {projeto['prazo'].strftime('%d/%m/%Y') if isinstance(projeto['prazo'], datetime.datetime) else projeto['prazo']}")
                    st.write(f"**Criado por:** {projeto['criado_por']}")
                    st.write(f"**Data de criação:** {projeto['data_criacao'].strftime('%d/%m/%Y %H:%M')}")
                    
                    # Indicador de próxima ação
                    if projeto['proxima_acao'] == st.session_state.user_role:
                        st.success(f"✅ É sua vez de agir neste projeto!")
                    else:
                        st.warning(f"⏳ Aguardando ação do {projeto['proxima_acao']}")
                
                with col2:
                    # Botões de ação baseados no papel do usuário e próxima ação
                    if st.session_state.user_role == "admin":
                        if st.button("📝 Editar", key=f"edit_{projeto['_id']}"):
                            st.session_state.editar_projeto = projeto['_id']
                            st.rerun()
                        
                        if st.button("🗑️ Excluir", key=f"delete_{projeto['_id']}"):
                            desativar_projeto(projeto['_id'])
                            st.success("Projeto excluído com sucesso!")
                            st.rerun()
                    
                    # Área de comentários
                    st.subheader("💬 Comentários")
                    
                    # Exibir comentários existentes
                    comentarios = obter_comentarios(projeto['_id'])
                    if comentarios:
                        for comentario in comentarios:
                            st.write(f"**{comentario['autor']}** ({comentario['data_criacao'].strftime('%d/%m/%Y %H:%M')}):")
                            st.write(f"{comentario['texto']}")
                            st.divider()
                    else:
                        st.info("Nenhum comentário ainda.")
                    
                    # Formulário para novo comentário
                    with st.form(key=f"comentario_form_{projeto['_id']}"):
                        novo_comentario = st.text_area("Novo comentário:", key=f"comentario_{projeto['_id']}")
                        enviar_comentario = st.form_submit_button("Enviar Comentário")
                        
                        if enviar_comentario and novo_comentario:
                            adicionar_comentario(projeto['_id'], novo_comentario, st.session_state.user_role)
                            st.success("Comentário adicionado com sucesso!")
                            st.rerun()
                
                # Se está editando este projeto
                if st.session_state.get('editar_projeto') == projeto['_id']:
                    st.subheader("✏️ Editar Projeto")
                    
                    with st.form(key=f"editar_form_{projeto['_id']}"):
                        novo_nome = st.text_input("Nome do projeto:", value=projeto['nome'])
                        nova_descricao = st.text_area("Descrição:", value=projeto['descricao'])
                        novo_responsavel = st.text_input("Responsável:", value=projeto['responsavel'])
                        novo_prazo = st.date_input("Prazo:", 
                                                 value=projeto['prazo'] if isinstance(projeto['prazo'], datetime.datetime) 
                                                 else datetime.datetime.now())
                        novo_status = st.selectbox("Status:", 
                                                 ["Em andamento", "Concluído", "Pausado", "Cancelado"],
                                                 index=["Em andamento", "Concluído", "Pausado", "Cancelado"].index(projeto['status']))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                atualizar_projeto(projeto['_id'], {
                                    "nome": novo_nome,
                                    "descricao": nova_descricao,
                                    "responsavel": novo_responsavel,
                                    "prazo": datetime.datetime.combine(novo_prazo, datetime.datetime.min.time()),
                                    "status": novo_status
                                })
                                del st.session_state.editar_projeto
                                st.success("Projeto atualizado com sucesso!")
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                del st.session_state.editar_projeto
                                st.rerun()
    else:
        st.info("Nenhum projeto cadastrado ainda.")

# Aba de criação de projetos (apenas para admin)
if st.session_state.user_role == "admin":
    with tab_criar:
        st.header("➕ Criar Novo Projeto")
        
        with st.form("form_criar_projeto"):
            nome_projeto = st.text_input("Nome do Projeto:*", placeholder="Digite o nome do projeto")
            descricao_projeto = st.text_area("Descrição:*", placeholder="Descreva o projeto", height=100)
            responsavel_projeto = st.text_input("Responsável:*", placeholder="Nome do responsável")
            prazo_projeto = st.date_input("Prazo:*", min_value=datetime.date.today())
            
            submitted = st.form_submit_button("Criar Projeto")
            if submitted:
                if nome_projeto and descricao_projeto and responsavel_projeto:
                    projeto_id = criar_projeto(
                        nome_projeto, 
                        descricao_projeto, 
                        responsavel_projeto, 
                        datetime.datetime.combine(prazo_projeto, datetime.datetime.min.time())
                    )
                    st.success(f"Projeto '{nome_projeto}' criado com sucesso!")
                    st.balloons()
                else:
                    st.error("Por favor, preencha todos os campos obrigatórios (*)")

with tab_dashboard:
    st.header("📈 Dashboard de Projetos")
    
    projetos = listar_projetos()
    if projetos:
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        total_projetos = len(projetos)
        projetos_em_andamento = len([p for p in projetos if p['status'] == 'Em andamento'])
        projetos_concluidos = len([p for p in projetos if p['status'] == 'Concluído'])
        minha_vez = len([p for p in projetos if p['proxima_acao'] == st.session_state.user_role])
        
        with col1:
            st.metric("Total de Projetos", total_projetos)
        with col2:
            st.metric("Em Andamento", projetos_em_andamento)
        with col3:
            st.metric("Concluídos", projetos_concluidos)
        with col4:
            st.metric("Minha Vez", minha_vez)
        
        # Gráfico de status (simulado)
        st.subheader("📊 Distribuição por Status")
        status_counts = {}
        for projeto in projetos:
            status = projeto['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            st.write(f"**{status}:** {count} projeto(s)")
        
        # Lista de projetos que exigem atenção
        st.subheader("🎯 Projetos que Precisam de Sua Atenção")
        projetos_minha_vez = [p for p in projetos if p['proxima_acao'] == st.session_state.user_role]
        
        if projetos_minha_vez:
            for projeto in projetos_minha_vez:
                st.write(f"**{projeto['nome']}** - Prazo: {projeto['prazo'].strftime('%d/%m/%Y')}")
                st.progress(50 if projeto['status'] == 'Em andamento' else 100)
        else:
            st.success("🎉 Nenhum projeto aguardando sua ação no momento!")
    
    else:
        st.info("Nenhum projeto cadastrado para exibir no dashboard.")

# --- Estilização ---
st.markdown("""
<style>
    .stExpander {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .stButton button {
        width: 100%;
        margin-bottom: 0.5rem;
    }
    .metric-container {
        text-align: center;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-weight: bold;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

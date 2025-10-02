import streamlit as st
import datetime
from pymongo import MongoClient
from bson import ObjectId

# Configuração inicial
st.set_page_config(
    layout="wide",
    page_title="Sistema de Acompanhamento de Projetos",
    page_icon="📊"
)

# --- Sistema de Autenticação SIMPLES ---
# Usuários hardcoded iniciais
default_users = {
    "admin": "admin123",  # admin/admin123
    "jose": "jose123",    # jose/jose123 - acesso a tudo
    "user": "user123"     # user/user123 - acesso limitado
}

def login():
    """Formulário de login"""
    st.title("🔐 Sistema de Acompanhamento de Projetos")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")
        
        if submit_button:
            # Verifica usuários padrão
            if username in default_users and password == default_users[username]:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.user_role = "admin" if username == "admin" else "user"
                st.success("Login realizado!")
                st.rerun()
            # Verifica usuários do banco
            elif "users_db" in st.session_state:
                user_data = st.session_state.users_db.find_one({"username": username, "ativo": True})
                if user_data and password == user_data["password"]:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.session_state.user_role = user_data["role"]
                    st.success("Login realizado!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")
            else:
                st.error("Usuário ou senha incorretos!")

# Verificar se o usuário está logado
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# --- CONEXÃO MONGODB (APÓS LOGIN) ---
try:
    client = MongoClient("mongodb+srv://gustavoromao3345:RqWFPNOJQfInAW1N@cluster0.5iilj.mongodb.net/auto_doc?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE&tlsAllowInvalidCertificates=true")
    db = client['projetos_app']
    collection_projetos = db['projetos']
    collection_comentarios = db['comentarios']
    collection_usuarios = db['usuarios']
    
    # Salvar no session state para acesso fácil
    st.session_state.users_db = collection_usuarios
    
    client.admin.command('ping')
    st.sidebar.success("✅ Conectado ao MongoDB")
    
except Exception as e:
    st.error(f"❌ Erro no MongoDB: {e}")
    st.stop()

# --- Funções para Usuários ---
def criar_usuario(username, password, role, projetos_acesso=None):
    """Cria um novo usuário"""
    if projetos_acesso is None:
        projetos_acesso = []
        
    usuario = {
        "username": username,
        "password": password,
        "role": role,
        "projetos_acesso": projetos_acesso,
        "data_criacao": datetime.datetime.now(),
        "criado_por": st.session_state.user,
        "ativo": True
    }
    result = collection_usuarios.insert_one(usuario)
    return result.inserted_id

def listar_usuarios():
    """Retorna todos os usuários ativos"""
    return list(collection_usuarios.find({"ativo": True}).sort("username", 1))

def obter_usuario(username):
    """Obtém um usuário específico"""
    return collection_usuarios.find_one({"username": username, "ativo": True})

def atualizar_usuario(username, dados_atualizacao):
    """Atualiza um usuário existente"""
    dados_atualizacao["data_atualizacao"] = datetime.datetime.now()
    return collection_usuarios.update_one(
        {"username": username},
        {"$set": dados_atualizacao}
    )

def desativar_usuario(username):
    """Desativa um usuário"""
    return collection_usuarios.update_one(
        {"username": username},
        {"$set": {"ativo": False, "data_desativacao": datetime.datetime.now()}}
    )

def usuario_tem_acesso(usuario, projeto_id):
    """Verifica se usuário tem acesso ao projeto"""
    if usuario == "admin" or usuario == "jose":
        return True
    
    user_data = obter_usuario(usuario)
    if not user_data:
        return False
    
    # Se não tem projetos específicos, tem acesso a tudo
    if not user_data.get("projetos_acesso"):
        return True
    
    # Verifica se o projeto_id está na lista de acesso
    projeto_id_str = str(projeto_id)
    return projeto_id_str in user_data["projetos_acesso"]

# --- Funções para Projetos ---
def criar_projeto(nome, descricao, responsavel, prazo, usuarios_acesso=None):
    """Cria um novo projeto no MongoDB"""
    if usuarios_acesso is None:
        usuarios_acesso = []
        
    projeto = {
        "nome": nome,
        "descricao": descricao,
        "responsavel": responsavel,
        "prazo": prazo,
        "usuarios_acesso": usuarios_acesso,  # Lista de usuários com acesso
        "status": "Em andamento",
        "proxima_acao": "admin",
        "data_criacao": datetime.datetime.now(),
        "criado_por": st.session_state.user,
        "ativo": True
    }
    result = collection_projetos.insert_one(projeto)
    
    # Atualiza os usuários com acesso a este projeto
    projeto_id_str = str(result.inserted_id)
    for username in usuarios_acesso:
        user_data = obter_usuario(username)
        if user_data:
            projetos_atual = user_data.get("projetos_acesso", [])
            if projeto_id_str not in projetos_atual:
                projetos_atual.append(projeto_id_str)
                atualizar_usuario(username, {"projetos_acesso": projetos_atual})
    
    return result.inserted_id

def listar_projetos():
    """Retorna projetos que o usuário tem acesso"""
    todos_projetos = list(collection_projetos.find({"ativo": True}).sort("data_criacao", -1))
    
    # Admin e Jose veem tudo
    if st.session_state.user in ["admin", "jose"]:
        return todos_projetos
    
    # Outros usuários veem apenas projetos com acesso
    projetos_com_acesso = []
    for projeto in todos_projetos:
        if usuario_tem_acesso(st.session_state.user, projeto['_id']):
            projetos_com_acesso.append(projeto)
    
    return projetos_com_acesso

def obter_projeto(projeto_id):
    """Obtém um projeto específico pelo ID"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    projeto = collection_projetos.find_one({"_id": projeto_id})
    
    # Verifica acesso
    if projeto and usuario_tem_acesso(st.session_state.user, projeto_id):
        return projeto
    return None

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
    """Desativa um projeto"""
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
    if autor != "admin":
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
st.sidebar.title(f"👋 {st.session_state.user}")
st.sidebar.write(f"**Tipo:** {st.session_state.user_role}")

# Botão de logout
if st.sidebar.button("🚪 Sair"):
    for key in ["logged_in", "user", "user_role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.title("📊 Sistema de Acompanhamento de Projetos")

# Menu de abas
if st.session_state.user == "admin":
    tab_projetos, tab_criar, tab_usuarios, tab_dashboard = st.tabs([
        "📋 Projetos", 
        "➕ Criar Projeto", 
        "👥 Gerenciar Usuários",
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
                    st.write(f"**Prazo:** {projeto['prazo'].strftime('%d/%m/%Y')}")
                    st.write(f"**Criado por:** {projeto['criado_por']}")
                    
                    # Mostrar usuários com acesso
                    if projeto.get('usuarios_acesso'):
                        st.write(f"**Acesso permitido para:** {', '.join(projeto['usuarios_acesso'])}")
                    
                    # Indicador de próxima ação
                    if projeto['proxima_acao'] == st.session_state.user:
                        st.success(f"✅ Sua vez de agir!")
                    else:
                        st.warning(f"⏳ Aguardando {projeto['proxima_acao']}")
                
                with col2:
                    # Botões de ação para admin
                    if st.session_state.user == "admin":
                        if st.button("📝 Editar", key=f"edit_{projeto['_id']}"):
                            st.session_state.editar_projeto = projeto['_id']
                            st.rerun()
                        
                        if st.button("🗑️ Excluir", key=f"delete_{projeto['_id']}"):
                            desativar_projeto(projeto['_id'])
                            st.success("Projeto excluído!")
                            st.rerun()
                    
                    # Área de comentários
                    st.subheader("💬 Comentários")
                    
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
                            adicionar_comentario(projeto['_id'], novo_comentario, st.session_state.user)
                            st.success("Comentário adicionado!")
                            st.rerun()
                
                # Edição de projeto
                if st.session_state.get('editar_projeto') == projeto['_id']:
                    st.subheader("✏️ Editar Projeto")
                    
                    # Buscar usuários disponíveis para seleção
                    usuarios_disponiveis = [u["username"] for u in listar_usuarios()]
                    
                    with st.form(key=f"editar_form_{projeto['_id']}"):
                        novo_nome = st.text_input("Nome:", value=projeto['nome'])
                        nova_descricao = st.text_area("Descrição:", value=projeto['descricao'])
                        novo_responsavel = st.text_input("Responsável:", value=projeto['responsavel'])
                        novo_prazo = st.date_input("Prazo:", value=projeto['prazo'])
                        usuarios_acesso = st.multiselect(
                            "Usuários com acesso:",
                            options=usuarios_disponiveis,
                            default=projeto.get('usuarios_acesso', [])
                        )
                        novo_status = st.selectbox(
                            "Status:", 
                            ["Em andamento", "Concluído", "Pausado", "Cancelado"],
                            index=["Em andamento", "Concluído", "Pausado", "Cancelado"].index(projeto['status'])
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Salvar"):
                                atualizar_projeto(projeto['_id'], {
                                    "nome": novo_nome,
                                    "descricao": nova_descricao,
                                    "responsavel": novo_responsavel,
                                    "prazo": datetime.datetime.combine(novo_prazo, datetime.datetime.min.time()),
                                    "usuarios_acesso": usuarios_acesso,
                                    "status": novo_status
                                })
                                del st.session_state.editar_projeto
                                st.success("Projeto atualizado!")
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancelar"):
                                del st.session_state.editar_projeto
                                st.rerun()
    else:
        st.info("Nenhum projeto disponível ou você não tem acesso a nenhum projeto.")

# Aba de criação de projetos (apenas para admin)
if st.session_state.user == "admin":
    with tab_criar:
        st.header("➕ Criar Novo Projeto")
        
        # Buscar usuários disponíveis para seleção
        usuarios_disponiveis = [u["username"] for u in listar_usuarios()]
        
        with st.form("form_criar_projeto"):
            nome_projeto = st.text_input("Nome do Projeto:*")
            descricao_projeto = st.text_area("Descrição:*", height=100)
            responsavel_projeto = st.text_input("Responsável:*")
            prazo_projeto = st.date_input("Prazo:*", min_value=datetime.date.today())
            usuarios_acesso = st.multiselect(
                "Usuários com acesso ao projeto:",
                options=usuarios_disponiveis,
                help="Selecione quais usuários podem ver e comentar neste projeto"
            )
            
            submitted = st.form_submit_button("Criar Projeto")
            if submitted:
                if nome_projeto and descricao_projeto and responsavel_projeto:
                    projeto_id = criar_projeto(
                        nome_projeto, 
                        descricao_projeto, 
                        responsavel_projeto, 
                        datetime.datetime.combine(prazo_projeto, datetime.datetime.min.time()),
                        usuarios_acesso
                    )
                    st.success(f"Projeto '{nome_projeto}' criado!")
                    st.balloons()
                else:
                    st.error("Preencha todos os campos obrigatórios!")

    with tab_usuarios:
        st.header("👥 Gerenciar Usuários")
        
        sub_tab1, sub_tab2 = st.tabs(["📋 Lista de Usuários", "➕ Criar Usuário"])
        
        with sub_tab1:
            st.subheader("Usuários do Sistema")
            
            usuarios = listar_usuarios()
            if usuarios:
                for usuario in usuarios:
                    with st.expander(f"👤 {usuario['username']} - {usuario['role']}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Tipo:** {usuario['role']}")
                            st.write(f"**Criado por:** {usuario['criado_por']}")
                            st.write(f"**Data criação:** {usuario['data_criacao'].strftime('%d/%m/%Y %H:%M')}")
                            
                            if usuario.get('projetos_acesso'):
                                st.write(f"**Acesso a projetos:** {len(usuario['projetos_acesso'])} projeto(s)")
                            else:
                                st.write("**Acesso:** Todos os projetos")
                        
                        with col2:
                            if st.button("🗑️ Excluir", key=f"del_user_{usuario['username']}"):
                                if usuario['username'] not in ['admin', 'jose', 'user']:
                                    desativar_usuario(usuario['username'])
                                    st.success(f"Usuário {usuario['username']} excluído!")
                                    st.rerun()
                                else:
                                    st.error("Não é possível excluir usuários padrão!")
            else:
                st.info("Nenhum usuário cadastrado além dos padrões.")
        
        with sub_tab2:
            st.subheader("Criar Novo Usuário")
            
            with st.form("form_criar_usuario"):
                novo_username = st.text_input("Nome de usuário:*")
                nova_senha = st.text_input("Senha:*", type="password")
                tipo_usuario = st.selectbox("Tipo de usuário:*", ["user", "admin"])
                
                submitted = st.form_submit_button("Criar Usuário")
                if submitted:
                    if novo_username and nova_senha:
                        if obter_usuario(novo_username):
                            st.error("Usuário já existe!")
                        else:
                            criar_usuario(novo_username, nova_senha, tipo_usuario)
                            st.success(f"Usuário '{novo_username}' criado!")
                            st.rerun()
                    else:
                        st.error("Preencha todos os campos!")

with tab_dashboard:
    st.header("📈 Dashboard de Projetos")
    
    projetos = listar_projetos()
    if projetos:
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        total_projetos = len(projetos)
        projetos_em_andamento = len([p for p in projetos if p['status'] == 'Em andamento'])
        projetos_concluidos = len([p for p in projetos if p['status'] == 'Concluído'])
        minha_vez = len([p for p in projetos if p['proxima_acao'] == st.session_state.user])
        
        with col1:
            st.metric("Total de Projetos", total_projetos)
        with col2:
            st.metric("Em Andamento", projetos_em_andamento)
        with col3:
            st.metric("Concluídos", projetos_concluidos)
        with col4:
            st.metric("Minha Vez", minha_vez)
        
        # Gráfico de status
        st.subheader("📊 Distribuição por Status")
        status_counts = {}
        for projeto in projetos:
            status = projeto['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            st.write(f"**{status}:** {count} projeto(s)")
        
        # Projetos que exigem atenção
        st.subheader("🎯 Projetos que Precisam de Sua Atenção")
        projetos_minha_vez = [p for p in projetos if p['proxima_acao'] == st.session_state.user]
        
        if projetos_minha_vez:
            for projeto in projetos_minha_vez:
                st.write(f"**{projeto['nome']}** - Prazo: {projeto['prazo'].strftime('%d/%m/%Y')}")
                st.progress(50 if projeto['status'] == 'Em andamento' else 100)
        else:
            st.success("🎉 Nenhum projeto aguardando sua ação!")
    
    else:
        st.info("Nenhum projeto para exibir no dashboard.")

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
</style>
""", unsafe_allow_html=True)

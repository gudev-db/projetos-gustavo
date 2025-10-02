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
default_users = {
    "admin": "admin123",
    "jose": "jose123", 
    "user": "user123"
}

def login():
    """Formulário de login"""
    st.title("🔐 Sistema de Acompanhamento de Projetos")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")
        
        if submit_button:
            if username in default_users and password == default_users[username]:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.user_role = "admin" if username == "admin" else "user"
                st.success("Login realizado!")
                st.rerun()
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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# --- CONEXÃO MONGODB ---
try:
    client = MongoClient("mongodb+srv://gustavoromao3345:RqWFPNOJQfInAW1N@cluster0.5iilj.mongodb.net/auto_doc?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE&tlsAllowInvalidCertificates=true")
    db = client['projetos_app']
    collection_projetos = db['projetos']
    collection_comentarios = db['comentarios']
    collection_usuarios = db['usuarios']
    
    st.session_state.users_db = collection_usuarios
    client.admin.command('ping')
    st.sidebar.success("✅ Conectado ao MongoDB")
    
except Exception as e:
    st.error(f"❌ Erro no MongoDB: {e}")
    st.stop()

# --- Funções para Usuários ---
def criar_usuario(username, password, role):
    """Cria um novo usuário"""
    usuario = {
        "username": username,
        "password": password,
        "role": role,
        "projetos_acesso": [],
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

def conceder_acesso_projeto(username, projeto_id):
    """Concede acesso a um projeto para um usuário"""
    user_data = obter_usuario(username)
    if user_data:
        projetos_atual = user_data.get("projetos_acesso", [])
        projeto_id_str = str(projeto_id)
        if projeto_id_str not in projetos_atual:
            projetos_atual.append(projeto_id_str)
            atualizar_usuario(username, {"projetos_acesso": projetos_atual})
            return True
    return False

def revogar_acesso_projeto(username, projeto_id):
    """Revoga acesso a um projeto de um usuário"""
    user_data = obter_usuario(username)
    if user_data:
        projetos_atual = user_data.get("projetos_acesso", [])
        projeto_id_str = str(projeto_id)
        if projeto_id_str in projetos_atual:
            projetos_atual.remove(projeto_id_str)
            atualizar_usuario(username, {"projetos_acesso": projetos_atual})
            return True
    return False

def usuario_tem_acesso(usuario, projeto_id):
    """Verifica se usuário tem acesso ao projeto"""
    if usuario in ["admin", "jose"]:
        return True
    
    user_data = obter_usuario(usuario)
    if not user_data:
        return False
    
    # Se não tem projetos específicos, tem acesso a tudo
    if not user_data.get("projetos_acesso"):
        return True
    
    projeto_id_str = str(projeto_id)
    return projeto_id_str in user_data["projetos_acesso"]

def obter_projetos_usuario(username):
    """Retorna todos os projetos que um usuário tem acesso"""
    user_data = obter_usuario(username)
    if not user_data or username in ["admin", "jose"]:
        return listar_projetos_todos()
    
    projetos_acesso_ids = user_data.get("projetos_acesso", [])
    projetos_com_acesso = []
    
    for projeto_id_str in projetos_acesso_ids:
        try:
            projeto = obter_projeto(ObjectId(projeto_id_str))
            if projeto:
                projetos_com_acesso.append(projeto)
        except:
            continue
    
    return projetos_com_acesso

# --- Funções para Projetos ---
def listar_projetos_todos():
    """Retorna TODOS os projetos (apenas para admin)"""
    return list(collection_projetos.find({"ativo": True}).sort("data_criacao", -1))

def criar_projeto(nome, descricao, responsavel, prazo):
    """Cria um novo projeto"""
    projeto = {
        "nome": nome,
        "descricao": descricao,
        "responsavel": responsavel,
        "prazo": prazo,
        "status": "Em andamento",
        "proxima_acao": "admin",
        "data_criacao": datetime.datetime.now(),
        "criado_por": st.session_state.user,
        "ativo": True
    }
    result = collection_projetos.insert_one(projeto)
    return result.inserted_id

def listar_projetos():
    """Retorna projetos que o usuário tem acesso"""
    if st.session_state.user in ["admin", "jose"]:
        return listar_projetos_todos()
    return obter_projetos_usuario(st.session_state.user)

def obter_projeto(projeto_id):
    """Obtém um projeto específico"""
    if isinstance(projeto_id, str):
        projeto_id = ObjectId(projeto_id)
    return collection_projetos.find_one({"_id": projeto_id, "ativo": True})

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
    """Alterna a próxima ação"""
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

if st.sidebar.button("🚪 Sair"):
    for key in ["logged_in", "user", "user_role"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

st.title("📊 Sistema de Acompanhamento de Projetos")

# Menu de abas
if st.session_state.user == "admin":
    tab_projetos, tab_criar, tab_usuarios, tab_permissoes, tab_dashboard = st.tabs([
        "📋 Projetos", 
        "➕ Criar Projeto", 
        "👥 Usuários",
        "🔐 Gerenciar Acessos", 
        "📈 Dashboard"
    ])
else:
    tab_projetos, tab_dashboard = st.tabs(["📋 Projetos", "📈 Dashboard"])

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
                    
                    if projeto['proxima_acao'] == st.session_state.user:
                        st.success(f"✅ Sua vez de agir!")
                    else:
                        st.warning(f"⏳ Aguardando {projeto['proxima_acao']}")
                
                with col2:
                    if st.session_state.user == "admin":
                        if st.button("📝 Editar", key=f"edit_{projeto['_id']}"):
                            st.session_state.editar_projeto = projeto['_id']
                            st.rerun()
                        
                        if st.button("🗑️ Excluir", key=f"delete_{projeto['_id']}"):
                            desativar_projeto(projeto['_id'])
                            st.success("Projeto excluído!")
                            st.rerun()
                    
                    st.subheader("💬 Comentários")
                    
                    comentarios = obter_comentarios(projeto['_id'])
                    if comentarios:
                        for comentario in comentarios:
                            st.write(f"**{comentario['autor']}** ({comentario['data_criacao'].strftime('%d/%m/%Y %H:%M')}):")
                            st.write(f"{comentario['texto']}")
                            st.divider()
                    else:
                        st.info("Nenhum comentário ainda.")
                    
                    with st.form(key=f"comentario_form_{projeto['_id']}"):
                        novo_comentario = st.text_area("Novo comentário:", key=f"comentario_{projeto['_id']}")
                        enviar_comentario = st.form_submit_button("Enviar Comentário")
                        
                        if enviar_comentario and novo_comentario:
                            adicionar_comentario(projeto['_id'], novo_comentario, st.session_state.user)
                            st.success("Comentário adicionado!")
                            st.rerun()
                
                if st.session_state.get('editar_projeto') == projeto['_id']:
                    st.subheader("✏️ Editar Projeto")
                    
                    with st.form(key=f"editar_form_{projeto['_id']}"):
                        novo_nome = st.text_input("Nome:", value=projeto['nome'])
                        nova_descricao = st.text_area("Descrição:", value=projeto['descricao'])
                        novo_responsavel = st.text_input("Responsável:", value=projeto['responsavel'])
                        novo_prazo = st.date_input("Prazo:", value=projeto['prazo'])
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
        st.info("Nenhum projeto disponível.")

if st.session_state.user == "admin":
    with tab_criar:
        st.header("➕ Criar Novo Projeto")
        
        with st.form("form_criar_projeto"):
            nome_projeto = st.text_input("Nome do Projeto:*")
            descricao_projeto = st.text_area("Descrição:*", height=100)
            responsavel_projeto = st.text_input("Responsável:*")
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
                    st.success(f"Projeto '{nome_projeto}' criado!")
                    st.balloons()
                else:
                    st.error("Preencha todos os campos!")

    with tab_usuarios:
        st.header("👥 Gerenciar Usuários")
        
        sub_tab1, sub_tab2 = st.tabs(["📋 Lista de Usuários", "➕ Criar Usuário"])
        
        with sub_tab1:
            st.subheader("Usuários do Sistema")
            
            usuarios = listar_usuarios()
            usuarios_padrao = ["admin", "jose", "user"]
            
            if usuarios:
                for usuario in usuarios:
                    with st.expander(f"👤 {usuario['username']} - {usuario['role']}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Tipo:** {usuario['role']}")
                            st.write(f"**Criado por:** {usuario['criado_por']}")
                            st.write(f"**Data criação:** {usuario['data_criacao'].strftime('%d/%m/%Y %H:%M')}")
                            
                            projetos_acesso = obter_projetos_usuario(usuario['username'])
                            st.write(f"**Tem acesso a:** {len(projetos_acesso)} projeto(s)")
                        
                        with col2:
                            if usuario['username'] not in usuarios_padrao:
                                if st.button("🗑️ Excluir", key=f"del_user_{usuario['username']}"):
                                    desativar_usuario(usuario['username'])
                                    st.success(f"Usuário {usuario['username']} excluído!")
                                    st.rerun()
                            else:
                                st.info("Usuário padrão")
            
            st.subheader("Usuários Padrão do Sistema")
            for user_padrao in usuarios_padrao:
                st.write(f"👤 **{user_padrao}** - Senha: {default_users[user_padrao]}")
        
        with sub_tab2:
            st.subheader("Criar Novo Usuário")
            
            with st.form("form_criar_usuario"):
                novo_username = st.text_input("Nome de usuário:*")
                nova_senha = st.text_input("Senha:*", type="password")
                tipo_usuario = st.selectbox("Tipo de usuário:*", ["user", "admin"])
                
                submitted = st.form_submit_button("Criar Usuário")
                if submitted:
                    if novo_username and nova_senha:
                        if obter_usuario(novo_username) or novo_username in default_users:
                            st.error("Usuário já existe!")
                        else:
                            criar_usuario(novo_username, nova_senha, tipo_usuario)
                            st.success(f"Usuário '{novo_username}' criado!")
                            st.rerun()
                    else:
                        st.error("Preencha todos os campos!")

    with tab_permissoes:
        st.header("🔐 Gerenciar Acessos aos Projetos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Todos os Projetos")
            projetos = listar_projetos_todos()
            
            if projetos:
                projeto_selecionado = st.selectbox(
                    "Selecione um projeto:",
                    options=[p["nome"] for p in projetos],
                    key="projeto_permissoes"
                )
                
                if projeto_selecionado:
                    projeto = next(p for p in projetos if p["nome"] == projeto_selecionado)
                    st.write(f"**Descrição:** {projeto['descricao']}")
                    st.write(f"**Status:** {projeto['status']}")
                    
                    # Mostrar quem tem acesso atualmente
                    st.subheader("👥 Usuários com Acesso")
                    usuarios_com_acesso = []
                    todos_usuarios = listar_usuarios() + [{"username": "jose"}, {"username": "user"}]
                    
                    for usuario in todos_usuarios:
                        username = usuario["username"]
                        if usuario_tem_acesso(username, projeto['_id']):
                            usuarios_com_acesso.append(username)
                    
                    if usuarios_com_acesso:
                        for username in usuarios_com_acesso:
                            st.write(f"✅ {username}")
                    else:
                        st.info("Nenhum usuário com acesso específico")
        
        with col2:
            st.subheader("👤 Conceder/Revogar Acesso")
            
            if projetos and projeto_selecionado:
                projeto = next(p for p in projetos if p["nome"] == projeto_selecionado)
                
                # Lista de usuários disponíveis (excluindo admin e jose que têm acesso total)
                usuarios_disponiveis = [u["username"] for u in listar_usuarios() if u["username"] not in ["admin", "jose"]]
                usuarios_disponiveis.extend(["user"])  # Adiciona o user padrão
                
                usuario_selecionado = st.selectbox(
                    "Selecione um usuário:",
                    options=usuarios_disponiveis,
                    key="usuario_permissoes"
                )
                
                if usuario_selecionado:
                    tem_acesso = usuario_tem_acesso(usuario_selecionado, projeto['_id'])
                    
                    if tem_acesso:
                        st.warning(f"❌ {usuario_selecionado} já tem acesso a este projeto")
                        if st.button("Revogar Acesso", type="primary"):
                            if revogar_acesso_projeto(usuario_selecionado, projeto['_id']):
                                st.success(f"Acesso revogado para {usuario_selecionado}!")
                                st.rerun()
                            else:
                                st.error("Erro ao revogar acesso")
                    else:
                        st.success(f"✅ {usuario_selecionado} pode receber acesso")
                        if st.button("Conceder Acesso", type="primary"):
                            if conceder_acesso_projeto(usuario_selecionado, projeto['_id']):
                                st.success(f"Acesso concedido para {usuario_selecionado}!")
                                st.rerun()
                            else:
                                st.error("Erro ao conceder acesso")
                
                # Acesso em massa
                st.subheader("🎯 Acesso Rápido")
                usuarios_para_acesso = st.multiselect(
                    "Selecionar múltiplos usuários:",
                    options=usuarios_disponiveis
                )
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Conceder a Todos") and usuarios_para_acesso:
                        for username in usuarios_para_acesso:
                            conceder_acesso_projeto(username, projeto['_id'])
                        st.success(f"Acesso concedido para {len(usuarios_para_acesso)} usuários!")
                        st.rerun()
                
                with col_b:
                    if st.button("❌ Revogar de Todos") and usuarios_para_acesso:
                        for username in usuarios_para_acesso:
                            revogar_acesso_projeto(username, projeto['_id'])
                        st.success(f"Acesso revogado de {len(usuarios_para_acesso)} usuários!")
                        st.rerun()

with tab_dashboard:
    st.header("📈 Dashboard de Projetos")
    
    projetos = listar_projetos()
    if projetos:
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
        
        st.subheader("📊 Distribuição por Status")
        status_counts = {}
        for projeto in projetos:
            status = projeto['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            st.write(f"**{status}:** {count} projeto(s)")
        
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

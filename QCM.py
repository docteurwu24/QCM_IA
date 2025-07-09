import streamlit as st
import google.generativeai as genai
import random
import json
import re

# --- Configuration de la page Streamlit ---
st.set_page_config(
    page_title="Générateur de QCM (Google Gemini)",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Fonctions Utilitaires ---

def generate_qcm_with_gemini(fragment, gemini_model):
    """
    Appelle l'API Google Gemini pour générer un QCM à partir d'un fragment de texte.
    Retourne un dictionnaire structuré ou None en cas d'échec.
    """
    prompt = f"""
    En te basant sur le fragment de texte suivant, crée un Questionnaire à Choix Multiples (QCM) complexe et pertinent.

    Fragment de texte :
    ---
    {fragment}
    ---

    Instructions pour le QCM :
    1.  Le QCM doit comporter 5 options de réponse (A, B, C, D, E).
    2.  Il doit y avoir UNE ou PLUSIEURS bonnes réponses.
    3.  La question doit porter sur un concept clé du texte.
    4.  Pour CHAQUE option (A, B, C, D, E), fournis une explication concise justifiant pourquoi elle est correcte ou incorrecte.

    Format de sortie OBLIGATOIRE (JSON strict) :
    Assure-toi que la réponse est *uniquement* le JSON valide, sans aucun texte supplémentaire, préambule ou postambule, ni bloc de code Markdown (comme ```json ... ```).

    {{
      "question": "Le texte de la question...",
      "options": {{
        "A": "Texte de l'option A",
        "B": "Texte de l'option B",
        "C": "Texte de l'option C",
        "D": "Texte de l'option D",
        "E": "Texte de l'option E"
      }},
      "correct_answers": ["A", "C"], // Liste des clés des bonnes réponses
      "explanations": {{
        "A": "Explication pour A...",
        "B": "Explication pour B...",
        "C": "Explication pour C...",
        "D": "Explication pour D...",
        "E": "Explication pour E..."
      }}
    }}
    """

    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.6,
            )
        )
        
        qcm_json_string = response.text.strip()
        if qcm_json_string.startswith('```json'):
            qcm_json_string = qcm_json_string[len('```json'):].strip()
        if qcm_json_string.endswith('```'):
            qcm_json_string = qcm_json_string[:-len('```')].strip()

        qcm_data = json.loads(qcm_json_string)
        
        qcm_data['fragment_source'] = fragment 
        return qcm_data
    except json.JSONDecodeError as e:
        st.error(f"Erreur de décodage JSON de la réponse de Gemini. Réponse brute : '{response.text}' Erreur: {e}")
        return None
    except Exception as e:
        st.error(f"Erreur lors de la génération du QCM avec l'API Google Gemini : {e}")
        return None

# --- Initialisation du Session State ---
if 'course_lines' not in st.session_state:
    st.session_state.course_lines = []
if 'current_qcm' not in st.session_state:
    st.session_state.current_qcm = None
if 'show_correction' not in st.session_state:
    st.session_state.show_correction = False
if 'user_selection' not in st.session_state:
    st.session_state.user_selection = []


# --- Interface Utilisateur (UI) ---

st.title("🧪 Générateur de QCM AI")
st.markdown("Chargez un cours au format `.txt` pour générer des QCM interactifs.")

# --- Barre Latérale (Sidebar) ---
with st.sidebar:
    st.header("Configuration")
    
    api_key = st.text_input("Clé API Google Gemini", type="password", help="Votre clé ne sera pas sauvegardée.")
    
    course_text_input = st.text_area("Collez votre cours ici", height=250)
    st.markdown("<p style='text-align: center; color: grey;'>OU</p>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Chargez un fichier .txt", type="txt")

    if st.button("🔬 Analyser le cours", use_container_width=True):
        course_text = ""
        if uploaded_file:
            course_text = uploaded_file.read().decode("utf-8")
        elif course_text_input:
            course_text = course_text_input
        
        if not course_text.strip():
            st.warning("Veuillez fournir du texte pour l'analyse.")
            st.session_state.course_lines = []
        else:
            with st.spinner("Analyse du cours en cours..."):
                all_lines = course_text.splitlines()
                st.session_state.course_lines = [line for line in all_lines if line.strip()]

            if not st.session_state.course_lines:
                st.error("Aucune ligne de texte non-vide n'a été trouvée.")
            else:
                st.success(f"{len(st.session_state.course_lines)} lignes de cours prêtes à être utilisées !")
                st.session_state.current_qcm = None
                st.session_state.show_correction = False

# --- Logique Principale ---
if api_key:
    try:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash') 
    except Exception as e:
        st.error(f"Erreur de configuration de l'API Google Gemini : {e}. Vérifiez votre clé API.")
        gemini_model = None
else:
    gemini_model = None


if gemini_model and st.session_state.course_lines:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("")
    with col2:
        if st.button("♻️ Générer un nouveau QCM", use_container_width=True):
            st.session_state.show_correction = False
            st.session_state.user_selection = []
            
            lines = st.session_state.course_lines
            num_lines = len(lines)
            chunk_size = 100 

            if num_lines == 0:
                 st.warning("Aucune ligne de cours à utiliser. Veuillez analyser un cours d'abord.")
                 st.session_state.current_qcm = None
            else:
                if num_lines <= chunk_size:
                    start_index = 0
                else:
                    max_start_index = num_lines - chunk_size
                    start_index = random.randint(0, max_start_index)
                
                selected_lines = lines[start_index : start_index + chunk_size]
                selected_fragment = "\n".join(selected_lines)

                with st.spinner("L'IA génère un QCM pertinent avec Gemini..."):
                    qcm = generate_qcm_with_gemini(selected_fragment, gemini_model)
                    st.session_state.current_qcm = qcm
                    
elif st.session_state.course_lines and not api_key:
    st.warning("Veuillez saisir votre clé API Google Gemini pour générer les QCM.")

# --- Affichage du QCM ---
if st.session_state.current_qcm:
    qcm = st.session_state.current_qcm
    
    st.markdown("---")
    with st.expander("▶️ Afficher le fragment du cours utilisé pour ce QCM"):
        st.info(f"*{qcm['fragment_source']}*")

    st.subheader(qcm['question'])

    with st.form("qcm_form"):
        user_choices = []
        sorted_keys = sorted(qcm['options'].keys())
        for key in sorted_keys:
            value = qcm['options'][key]
            # Précoche les options si l'utilisateur a déjà soumis une réponse et que show_correction est active
            checked = key in st.session_state.user_selection if st.session_state.show_correction else False
            if st.checkbox(f"**{key}:** {value}", key=f"cb_{key}", value=checked):
                user_choices.append(key)
        
        if st.form_submit_button("✅ Valider ma réponse"):
            st.session_state.user_selection = sorted(user_choices)
            st.session_state.show_correction = True
            st.rerun()

# --- Affichage de la Correction ---
if st.session_state.show_correction and st.session_state.current_qcm:
    qcm = st.session_state.current_qcm
    user_answers = st.session_state.user_selection
    correct_answers = sorted(qcm['correct_answers'])
    
    st.markdown("---")
    st.subheader("Correction détaillée")

    # Message de succès ou d'échec global (inchangé)
    if user_answers == correct_answers:
        st.success("🎉 Bravo ! C'est la bonne réponse.")
    else:
        st.error("🤔 Votre réponse est incorrecte ou incomplète. Voici le détail :")

    # Affichage détaillé de la correction pour chaque option
    for key in sorted(qcm['options'].keys()):
        value = qcm['options'][key]
        explanation = qcm['explanations'].get(key, "Pas d'explication fournie.")
        
        # Déterminer si l'option est correcte dans l'absolu
        is_correct_option = key in correct_answers
        # Déterminer si l'utilisateur a sélectionné cette option
        user_selected_option = key in user_answers

        color = ""
        icon = ""
        status_text = ""

        if is_correct_option and user_selected_option:
            # J'ai coché vrai et c'est vrai -> Vert
            color = "rgba(40, 167, 69, 0.2)" # Vert clair
            icon = "✅"
            status_text = "Correcte (Votre choix)"
        elif is_correct_option and not user_selected_option:
            # J'ai mis faux (pas coché) alors que c'est vrai -> Rouge
            color = "rgba(220, 53, 69, 0.2)" # Rouge clair
            icon = "❌"
            status_text = "Correcte (Manquée)"
        elif not is_correct_option and user_selected_option:
            # J'ai mis vrai (coché) alors que c'est faux -> Rouge
            color = "rgba(220, 53, 69, 0.2)" # Rouge clair
            icon = "❌"
            status_text = "Incorrecte (Votre choix)"
        elif not is_correct_option and not user_selected_option:
            # J'ai mis faux (pas coché) et que c'est faux -> Vert
            color = "rgba(40, 167, 69, 0.2)" # Vert clair
            icon = "✅"
            status_text = "Incorrecte (Non sélectionnée)"
        
        st.markdown(f"<div style='background-color: {color}; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                    f"{icon} **Option {key} ({status_text})**: {value}<br>"
                    f"**Explication :** {explanation}</div>", unsafe_allow_html=True)
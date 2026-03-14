"""
Ui.py
=====
Simple Streamlit frontend for the BridgeWell API.

How to run:
    streamlit run Ui.py

Make sure your FastAPI backend is already running, for example:
    uvicorn main:app --reload

Default API URL:
    http://127.0.0.1:8000
"""

import requests
import streamlit as st


DEFAULT_API_URL = "http://127.0.0.1:8000"


def safe_get(base_url: str, endpoint: str, params=None):
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def safe_post(base_url: str, endpoint: str, payload: dict):
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def show_metric_row(data: dict):
    if not data:
        st.info("No data available.")
        return

    numeric_items = []
    for key, value in data.items():
        if isinstance(value, (int, float)) and key != "total_respondents":
            numeric_items.append((key, value))

    if not numeric_items:
        st.json(data)
        return

    cols = st.columns(min(4, len(numeric_items)))
    for i, (key, value) in enumerate(numeric_items[:4]):
        label = key.replace("_", " ").title()
        cols[i].metric(label, value)


def main():
    st.set_page_config(
        page_title="BridgeWell",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .subtle {
            color: #6b7280;
            margin-bottom: 1rem;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1rem;
            padding: 0.6rem 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="main-title">BridgeWell</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtle">Mental Health Employer Support Tool</div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Settings")
        base_url = st.text_input("API Base URL", value=DEFAULT_API_URL)
        st.caption("Example: http://127.0.0.1:8000")

        st.divider()
        st.subheader("Connection Check")
        if st.button("Check API Status", use_container_width=True):
            data, error = safe_get(base_url, "/")
            if error:
                st.error(f"Could not reach API: {error}")
            else:
                st.success(f"Connected: {data}")

        st.divider()
        st.markdown(
            """
            **Before using this app**
            1. Start your FastAPI backend  
            2. Make sure PostgreSQL and Neo4j are running  
            3. Then use the tabs on the right
            """
        )

    tabs = st.tabs(
        [
            "Overview",
            "Country Analysis",
            "Recommendations",
            "Graph View",
            "Register Company",
        ]
    )

    with tabs[0]:
        st.subheader("Welcome")
        st.write(
            "This interface lets employers and researchers explore country-level "
            "mental health data, view recommended wellbeing programs, inspect graph data, "
            "and register a company for tailored recommendations."
        )

        countries_data, countries_error = safe_get(base_url, "/countries")
        if countries_error:
            st.warning("Could not load countries yet. Start the API and try again.")
        else:
            countries = countries_data.get("countries", [])
            st.success(f"{len(countries)} countries available")
            if countries:
                st.dataframe({"Available Countries": countries}, use_container_width=True)

    with tabs[1]:
        st.subheader("Country Analysis")
        countries_data, countries_error = safe_get(base_url, "/countries")

        if countries_error:
            st.error(f"Could not load countries: {countries_error}")
        else:
            countries = countries_data.get("countries", [])
            selected_country = st.selectbox(
                "Choose a country",
                options=countries,
                key="analysis_country",
            )

            if st.button("Load Analysis", use_container_width=True):
                data, error = safe_get(base_url, f"/analysis/{selected_country}")
                if error:
                    st.error(f"Analysis request failed: {error}")
                else:
                    st.success(f"Loaded analysis for {selected_country}")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("### Employer Gap")
                        show_metric_row(data.get("employer_gap", {}))
                        st.json(data.get("employer_gap", {}))

                    with col2:
                        st.markdown("### Lifestyle Risk")
                        show_metric_row(data.get("lifestyle_risk", {}))
                        st.json(data.get("lifestyle_risk", {}))

                    with col3:
                        st.markdown("### Treatment Gap")
                        show_metric_row(data.get("treatment_gap", {}))
                        st.json(data.get("treatment_gap", {}))

    with tabs[2]:
        st.subheader("Program Recommendations")
        countries_data, countries_error = safe_get(base_url, "/countries")

        if countries_error:
            st.error(f"Could not load countries: {countries_error}")
        else:
            countries = countries_data.get("countries", [])
            col1, col2 = st.columns([3, 1])

            with col1:
                selected_country = st.selectbox(
                    "Choose a country",
                    options=countries,
                    key="recommend_country",
                )
            with col2:
                remote_only = st.checkbox("Remote only", value=False)

            if st.button("Get Recommendations", use_container_width=True):
                data, error = safe_get(
                    base_url,
                    f"/recommendations/{selected_country}",
                    params={"remote_only": str(remote_only).lower()},
                )
                if error:
                    st.error(f"Recommendation request failed: {error}")
                else:
                    st.success(f"Loaded recommendations for {selected_country}")

                    who_context = data.get("who_context", {})
                    if who_context:
                        st.markdown("### WHO Context")
                        c1, c2, c3 = st.columns(3)
                        c1.metric(
                            "Psychiatrists per 100k",
                            who_context.get("psychiatrists_per_100k", "N/A"),
                        )
                        c2.metric(
                            "Mental Health Budget %",
                            who_context.get("mh_budget_pct", "N/A"),
                        )
                        c3.metric(
                            "Mental Health Policy",
                            who_context.get("has_mh_policy", "N/A"),
                        )

                    programs = data.get("programs", [])
                    st.markdown("### Recommended Programs")
                    if not programs:
                        st.info(data.get("message", "No programs found."))
                    else:
                        for i, program in enumerate(programs, start=1):
                            with st.expander(f"{i}. {program.get('name', 'Unnamed Program')}"):
                                st.write(f"**Program Type:** {program.get('program_type', 'N/A')}")
                                st.write(f"**Description:** {program.get('description', 'N/A')}")
                                st.write(f"**Remote OK:** {program.get('remote_ok', 'N/A')}")
                                st.write(f"**Coverage Score:** {program.get('coverage_score', 'N/A')}")
                                st.write("**Addressed Needs:**")
                                st.write(program.get("addressed_needs", []))
                                st.write("**Government Datasets:**")
                                st.write(program.get("gov_datasets", []))

    with tabs[3]:
        st.subheader("Graph View")
        countries_data, countries_error = safe_get(base_url, "/countries")

        if countries_error:
            st.error(f"Could not load countries: {countries_error}")
        else:
            countries = countries_data.get("countries", [])
            selected_country = st.selectbox(
                "Choose a country",
                options=countries,
                key="graph_country",
            )

            if st.button("Load Graph Data", use_container_width=True):
                data, error = safe_get(base_url, f"/graph/{selected_country}")
                if error:
                    st.error(f"Graph request failed: {error}")
                else:
                    st.success(f"Loaded graph data for {selected_country}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### Survey Snapshot")
                        st.json(data.get("survey", {}))

                        st.markdown("### WHO Profile")
                        st.json(data.get("who", {}))

                    with col2:
                        st.markdown("### Needs")
                        st.json(data.get("needs", []))

                        st.markdown("### Programs")
                        st.json(data.get("programs", []))

                    st.markdown("### Facilities")
                    st.json(data.get("facilities", []))

    with tabs[4]:
        st.subheader("Register Company")
        st.write("Submit company information and receive tailored recommendations.")

        with st.form("company_form"):
            col1, col2 = st.columns(2)

            with col1:
                company_name = st.text_input("Company Name")
                country = st.text_input("Country")
                industry = st.text_input("Industry")

            with col2:
                size = st.selectbox(
                    "Company Size",
                    ["1-10", "11-50", "51-200", "201-500", "500+"],
                )
                remote_policy = st.selectbox("Remote Policy", ["yes", "no", "hybrid"])
                company_id = st.text_input("Company ID (optional)")

            submitted = st.form_submit_button("Register Company", use_container_width=True)

        if submitted:
            if not company_name or not country or not industry:
                st.error("Please fill in Company Name, Country, and Industry.")
            else:
                payload = {
                    "name": company_name,
                    "country": country,
                    "industry": industry,
                    "size": size,
                    "remote_policy": remote_policy,
                    "company_id": company_id if company_id else None,
                }

                data, error = safe_post(base_url, "/company", payload)
                if error:
                    st.error(f"Company registration failed: {error}")
                else:
                    st.success("Company registered successfully")

                    st.markdown("### Company Summary")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Company ID", data.get("company_id", "N/A"))
                    c2.metric("Company Name", data.get("company_name", "N/A"))
                    c3.metric("Country", data.get("country", "N/A"))

                    st.markdown("### Country Context")
                    st.json(data.get("country_context", {}))

                    st.markdown("### WHO Context")
                    st.json(data.get("who_context", {}))

                    st.markdown("### Recommendations")
                    recommendations = data.get("recommendations", [])
                    if not recommendations:
                        st.info("No recommendations returned.")
                    else:
                        for i, rec in enumerate(recommendations, start=1):
                            with st.expander(f"{i}. {rec.get('name', 'Unnamed Program')}"):
                                st.json(rec)


if __name__ == "__main__":
    main()

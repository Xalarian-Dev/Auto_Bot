"""
Auto_Bot Scout — Streamlit dashboard.
Launch with: .venv/Scripts/streamlit run app.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
import pandas as pd
import streamlit as st
import yaml
from dotenv import load_dotenv

load_dotenv()

from scout.db import get_all_modes, get_stats, get_top_listings, update_status
from scout.models import JobListingORM, JobStatus
from scout.runner import MODE_LABELS
from config.profile_generator import generate_criteria

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Auto_Bot Scout",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = os.getenv("DB_PATH", "data/scout.db")
CONFIG_PATH = os.getenv("CONFIG_PATH", "config/criteria.yaml")
PROFILES_PATH = os.getenv("PROFILES_PATH", "config/mode_profiles.yaml")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("🔍 Auto_Bot Scout")
st.sidebar.markdown("---")

page = st.sidebar.radio("View", ["Dashboard", "Mode Editor"])

st.sidebar.markdown("---")

mode_options = ["All", "A — APAC", "B — North America", "C — Europe"]
selected_mode_label = st.sidebar.radio("Mode", mode_options)
selected_mode = None if selected_mode_label == "All" else selected_mode_label[0]

st.sidebar.markdown("---")
min_score = st.sidebar.slider("Minimum score", min_value=0, max_value=100, value=60, step=5)
reloc_only = st.sidebar.checkbox("Relocation-friendly only", value=False)

status_options = {
    "Active (new)": JobStatus.NEW,
    "Applied": JobStatus.APPLIED,
    "Ignored": JobStatus.IGNORED,
    "All": None,
}
selected_status_label = st.sidebar.radio("Status filter", list(status_options.keys()))
selected_status = status_options[selected_status_label]

st.sidebar.markdown("---")
st.sidebar.markdown("**Run Scout**")
run_mode = st.sidebar.selectbox("Select mode to run", ["A — APAC", "B — North America", "C — Europe"])
dry_run = st.sidebar.checkbox("Dry run (no save, no scoring)")
run_clicked = st.sidebar.button("▶ Run Scout", type="primary", use_container_width=True)

# ===========================================================================
# PAGE — Dashboard
# ===========================================================================

if page == "Dashboard":

    st.title("🔍 Scout Dashboard")

    mode_display = f"Mode {selected_mode} — {MODE_LABELS[selected_mode]}" if selected_mode else "All Modes"
    st.caption(f"Showing: {mode_display}  |  Min score: {min_score}  |  DB: `{DB_PATH}`")

    # -----------------------------------------------------------------------
    # Stats row
    # -----------------------------------------------------------------------

    modes_with_data = get_all_modes(DB_PATH)

    if modes_with_data:
        cols = st.columns(len(modes_with_data) if not selected_mode else 1)
        display_modes = [selected_mode] if selected_mode else modes_with_data

        for i, mode in enumerate(display_modes):
            stats = get_stats(DB_PATH, scout_mode=mode)
            label = MODE_LABELS.get(mode, mode)
            with cols[i] if not selected_mode else cols[0]:
                st.markdown(f"**Mode {mode} — {label}**")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total", stats["total"])
                m2.metric("Scored", stats["scored"])
                m3.metric("Unscored", stats["unscored"])
                m4.metric("Avg Score", stats["avg_score"])
    else:
        st.info("No data in database yet. Run the Scout to fetch listings.")

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Run Scout
    # -----------------------------------------------------------------------

    if run_clicked:
        mode_key = run_mode[0]
        cmd = [sys.executable, "main.py", "--mode", mode_key]
        if dry_run:
            cmd.append("--dry-run")

        st.subheader(f"Running Scout — Mode {mode_key}")
        output_box = st.empty()
        output_lines: list[str] = []

        with st.spinner(f"Fetching and scoring Mode {mode_key}..."):
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            for line in proc.stdout:  # type: ignore[union-attr]
                output_lines.append(line.rstrip())
                output_box.code("\n".join(output_lines[-40:]), language=None)
            proc.wait()

        if proc.returncode == 0:
            st.success("Scout run complete. Refresh to see updated results.")
        else:
            st.error(f"Scout exited with code {proc.returncode}.")

        st.markdown("---")

    # -----------------------------------------------------------------------
    # Listings table
    # -----------------------------------------------------------------------

    st.subheader("Top Listings")

    listings: list[JobListingORM] = get_top_listings(
        min_score=min_score,
        limit=200,
        db_path=DB_PATH,
        scout_mode=selected_mode,
        status=selected_status,
    )

    if reloc_only:
        listings = [j for j in listings if j.is_relocation_friendly]

    if not listings:
        st.info(f"No listings with score ≥ {min_score} found.")
    else:
        st.caption(f"{len(listings)} listing(s)")

        rows = []
        for job in listings:
            rows.append({
                "Score": job.relevance_score,
                "Mode": job.scout_mode,
                "Title": job.title,
                "Company": job.company,
                "Location": job.location,
                "Source": job.source,
                "Reloc": "✓" if job.is_relocation_friendly else "✗",
                "Posted": job.date_posted.strftime("%Y-%m-%d") if job.date_posted else "",
                "URL": job.url,
                "Notes": job.relevance_notes or "",
            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.NumberColumn(width="small"),
                "Mode": st.column_config.TextColumn(width="small"),
                "Title": st.column_config.TextColumn(width="large"),
                "Company": st.column_config.TextColumn(width="medium"),
                "Location": st.column_config.TextColumn(width="medium"),
                "Source": st.column_config.TextColumn(width="small"),
                "Reloc": st.column_config.TextColumn(width="small"),
                "Posted": st.column_config.TextColumn(width="small"),
                "URL": st.column_config.LinkColumn("URL", width="small"),
                "Notes": st.column_config.TextColumn(width="large"),
            },
        )

        st.markdown("**Quick actions**")
        action_options = {
            f"{job.relevance_score} | {job.title} @ {job.company}": job
            for job in listings
        }
        action_label = st.selectbox("Select a job", list(action_options.keys()), key="action_select")
        action_job = action_options[action_label]

        col_a, col_i, col_r = st.columns([1, 1, 1])
        with col_a:
            if st.button("✅ Mark as Applied", use_container_width=True):
                update_status(action_job.fingerprint, JobStatus.APPLIED, DB_PATH)
                st.success(f"Marked as Applied: {action_job.title}")
                st.rerun()
        with col_i:
            if st.button("🚫 Ignore", use_container_width=True):
                update_status(action_job.fingerprint, JobStatus.IGNORED, DB_PATH)
                st.success(f"Ignored: {action_job.title}")
                st.rerun()
        with col_r:
            if action_job.status != JobStatus.NEW:
                if st.button("↩ Restore to Active", use_container_width=True):
                    update_status(action_job.fingerprint, JobStatus.NEW, DB_PATH)
                    st.success(f"Restored: {action_job.title}")
                    st.rerun()

    # -----------------------------------------------------------------------
    # Drafter
    # -----------------------------------------------------------------------

    st.markdown("---")
    st.subheader("Draft Application")

    if not listings:
        st.info("No listings to draft for. Adjust filters above.")
    else:
        job_options = {
            f"{job.relevance_score} | {job.title} @ {job.company} ({job.location})": job
            for job in listings
        }

        selected_label = st.selectbox("Select a job to draft for", list(job_options.keys()))
        selected_job = job_options[selected_label]

        with st.expander("Job details", expanded=False):
            st.markdown(f"**URL:** [{selected_job.url}]({selected_job.url})")
            st.markdown(f"**Score:** {selected_job.relevance_score}  |  **Source:** {selected_job.source}")
            if selected_job.relevance_notes:
                st.markdown(f"**Scout notes:** {selected_job.relevance_notes}")
            if selected_job.description:
                st.text(selected_job.description[:1000])

        draft_clicked = st.button("Generate Cover Letter + Talking Points", type="primary")

        if draft_clicked:
            if not os.getenv("ANTHROPIC_API_KEY"):
                st.error("ANTHROPIC_API_KEY not set.")
            else:
                with st.spinner("Drafting with Claude Sonnet..."):
                    try:
                        from drafter.agent import DrafterAgent
                        from drafter.writer import save_cover_letter

                        agent = DrafterAgent()
                        result = agent.draft(
                            job_title=selected_job.title,
                            company=selected_job.company,
                            location=selected_job.location,
                            description=selected_job.description or "",
                            notes=selected_job.relevance_notes or "",
                            salary=selected_job.salary_raw or "",
                        )
                        pdf_path = save_cover_letter(result)

                        st.session_state["draft_result"] = result
                        st.session_state["draft_pdf_path"] = pdf_path

                    except Exception as exc:
                        st.error(f"Drafting failed: {exc}")

        if "draft_result" in st.session_state:
            result = st.session_state["draft_result"]
            pdf_path = st.session_state["draft_pdf_path"]

            st.success(f"Draft ready — {result.job_title} @ {result.company}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Cover Letter")
                st.text_area(
                    "Cover letter (editable)",
                    value=result.cover_letter,
                    height=400,
                    key="cover_letter_text",
                )
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="Download PDF",
                        data=f.read(),
                        file_name=pdf_path.split("\\")[-1].split("/")[-1],
                        mime="application/pdf",
                    )

            with col2:
                st.markdown("### Talking Points")
                if result.talking_points:
                    st.markdown(result.talking_points)
                else:
                    st.warning("No talking points were generated. Try regenerating — Claude occasionally skips this section.")

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------

    st.markdown("---")
    st.caption(f"Auto_Bot Scout · {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ===========================================================================
# PAGE — Mode Editor
# ===========================================================================

elif page == "Mode Editor":

    st.title("Mode Editor")
    st.caption(f"Editing: `{PROFILES_PATH}` — changes regenerate `{CONFIG_PATH}` on save.")

    # Load profiles
    try:
        with open(PROFILES_PATH, encoding="utf-8") as f:
            profiles = yaml.safe_load(f)
    except FileNotFoundError:
        st.error(f"Profile file not found: {PROFILES_PATH}")
        st.stop()

    mode_ids = list(profiles.get("modes", {}).keys())
    selected_mode_id = st.selectbox("Select mode to edit", mode_ids,
                                    format_func=lambda m: f"Mode {m} — {profiles['modes'][m].get('label', m)}")

    profile = profiles["modes"][selected_mode_id]

    st.markdown("---")

    # ---- Label & suffix ---------------------------------------------------
    col_l, col_s = st.columns(2)
    with col_l:
        new_label = st.text_input("Mode label", value=profile.get("label", ""))
    with col_s:
        new_suffix = st.text_input(
            "Search suffix (appended to each keyword query)",
            value=profile.get("search_suffix", ""),
            help='e.g. "relocation visa sponsorship" — added to SerpAPI/Jaabz queries',
        )

    st.markdown("---")

    # ---- Keywords ---------------------------------------------------------
    st.subheader("Keywords")
    st.caption("One keyword per line")
    keywords_text = st.text_area(
        "Keywords",
        value="\n".join(profile.get("keywords", [])),
        height=150,
        label_visibility="collapsed",
    )
    new_keywords = [k.strip() for k in keywords_text.splitlines() if k.strip()]

    st.markdown("---")

    # ---- Locations --------------------------------------------------------
    st.subheader("Locations")

    locations: list[dict] = list(profile.get("locations", []))

    # Display existing locations as editable rows
    updated_locations: list[dict] = []
    to_delete = set()

    for i, loc in enumerate(locations):
        c1, c2, c3, c4 = st.columns([3, 3, 2, 1])
        with c1:
            loc_name = st.text_input("City / Area", value=loc.get("name", ""), key=f"loc_name_{i}")
        with c2:
            loc_country = st.text_input("Country", value=loc.get("country", ""), key=f"loc_country_{i}")
        with c3:
            loc_domain = st.text_input("Indeed domain (opt.)", value=loc.get("indeed_domain", ""),
                                       key=f"loc_domain_{i}",
                                       help="Only for Mode C — e.g. nl.indeed.com")
        with c4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_loc_{i}"):
                to_delete.add(i)

        if i not in to_delete:
            entry = {"name": loc_name, "country": loc_country}
            if loc_domain:
                entry["indeed_domain"] = loc_domain
            updated_locations.append(entry)

    # Add new location
    with st.expander("+ Add location"):
        nc1, nc2, nc3 = st.columns([3, 3, 2])
        with nc1:
            new_loc_name = st.text_input("City / Area", key="new_loc_name")
        with nc2:
            new_loc_country = st.text_input("Country", key="new_loc_country")
        with nc3:
            new_loc_domain = st.text_input("Indeed domain (opt.)", key="new_loc_domain")
        if st.button("Add location"):
            if new_loc_name and new_loc_country:
                entry = {"name": new_loc_name, "country": new_loc_country}
                if new_loc_domain:
                    entry["indeed_domain"] = new_loc_domain
                updated_locations.append(entry)
                st.rerun()

    st.markdown("---")

    # ---- Sources ----------------------------------------------------------
    st.subheader("Sources")
    sources = profile.get("sources", {})
    source_keys = ["serpapi", "mcf", "jaabz", "globaljobs", "greenhouse",
                   "usajobs", "jobbank", "itjobboard", "indeed"]
    source_labels = {
        "serpapi": "SerpAPI / Google Jobs",
        "mcf": "MyCareersFuture (Singapore)",
        "jaabz": "Jaabz (relocation-focused)",
        "globaljobs": "GlobalJobs (NGO / international)",
        "greenhouse": "Greenhouse ATS",
        "usajobs": "USAJobs (US federal)",
        "jobbank": "Job Bank Canada",
        "itjobboard": "IT Job Board USA",
        "indeed": "Indeed EU (SerpAPI paid)",
    }
    new_sources = {}
    cols_src = st.columns(3)
    for j, key in enumerate(source_keys):
        with cols_src[j % 3]:
            new_sources[key] = st.checkbox(source_labels[key], value=sources.get(key, False), key=f"src_{key}")

    st.markdown("---")

    # ---- Greenhouse -------------------------------------------------------
    if new_sources.get("greenhouse"):
        st.subheader("Greenhouse Companies")
        st.caption("One per line — format: `token | Display Name`  (token = company slug in Greenhouse API)")

        gh_companies: list[dict] = profile.get("greenhouse_companies", [])
        gh_text = "\n".join(f"{c['token']} | {c['name']}" for c in gh_companies)
        new_gh_text = st.text_area("Companies", value=gh_text, height=150)

        new_gh_companies = []
        for line in new_gh_text.splitlines():
            line = line.strip()
            if "|" in line:
                token, name = line.split("|", 1)
                new_gh_companies.append({"token": token.strip(), "name": name.strip()})

        st.subheader("Greenhouse Title Filters")
        st.caption("One keyword per line — only jobs whose title contains one of these are kept")
        gh_filters = profile.get("greenhouse_title_filters", [])
        new_gh_filters_text = st.text_area("Title filters", value="\n".join(gh_filters), height=120)
        new_gh_filters = [f.strip() for f in new_gh_filters_text.splitlines() if f.strip()]
    else:
        new_gh_companies = profile.get("greenhouse_companies", [])
        new_gh_filters = profile.get("greenhouse_title_filters", [])

    st.markdown("---")

    # ---- Save -------------------------------------------------------------
    if st.button("💾 Save & Regenerate criteria.yaml", type="primary"):
        # Build updated profile
        profiles["modes"][selected_mode_id] = {
            "label": new_label,
            "search_suffix": new_suffix,
            "keywords": new_keywords,
            "locations": updated_locations,
            "sources": new_sources,
            "greenhouse_companies": new_gh_companies,
            "greenhouse_title_filters": new_gh_filters,
        }

        # Write mode_profiles.yaml
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            yaml.dump(profiles, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        # Regenerate criteria.yaml
        try:
            generate_criteria(profiles_path=PROFILES_PATH, output_path=CONFIG_PATH)
            st.success(f"Saved! `{PROFILES_PATH}` updated and `{CONFIG_PATH}` regenerated.")
        except Exception as exc:
            st.error(f"Profile saved but criteria.yaml generation failed: {exc}")

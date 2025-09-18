"""Streamlit GUI for PoGo Analyzer (quick checks and PvP scoreboard helper).

Run with either:

  streamlit run pogo_analyzer/gui_app.py
  # or, after installing the launcher: pogo-analyzer-gui

Install extras:

  pip install .[gui]
"""

from __future__ import annotations

from typing import Sequence


def main(argv: Sequence[str] | None = None) -> None:  # pragma: no cover - UI only
    try:
        import streamlit as st
    except Exception as exc:  # noqa: BLE001 - user-friendly guidance
        raise SystemExit(
            "Streamlit is required for the GUI. Install with `pip install pogo-analyzer[gui]`\n"
            "Then run: streamlit run pogo_analyzer/gui_app.py or `pogo-analyzer-gui`"
        ) from exc

    st.set_page_config(page_title="PoGo Analyzer", layout="wide")
    # Theme tokens, spacing scale, subtle elevation, and utility classes
    st.markdown(
        """
        <style>
        :root{
          --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:24px;
          --radius:12px; --elev:0 6px 18px rgba(0,0,0,.10);
          --primary:#3F7CEC; --success:#2FBF71; --warn:#FFB020; --error:#E5484D;
        }
        .card{border-radius:var(--radius); padding:var(--space-4); box-shadow:var(--elev); background:rgba(255,255,255,.03);}
        .badge{display:inline-block; padding:2px 8px; border-radius:999px; background:rgba(255,255,255,.08); margin-right:6px;}
        .section{margin-top:var(--space-5); margin-bottom:var(--space-4);}        
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Sticky header keeps key controls visible on scroll
    st.markdown(
        '<div style="position:sticky;top:0;z-index:999;background:var(--bg,#0f1116);padding:8px 0;'
        'border-bottom:1px solid rgba(255,255,255,.06)">',
        unsafe_allow_html=True,
    )
    st.title("PoGo Analyzer")
    st.caption("Quick checks (PvE/PvP) and scoreboards with clear, guided controls.")
    st.markdown("</div>", unsafe_allow_html=True)

    tabs = st.tabs(["Quick Check", "Raid Scoreboard", "PvP Scoreboard", "About"])

    with tabs[0]:
        _tab_single_pokemon(st)

    with tabs[1]:
        _tab_raid_scoreboard(st)

    with tabs[2]:
        _tab_pvp_scoreboard(st)

    with tabs[3]:
        st.markdown(
            """
            - This GUI wraps the same library used by the CLI.
            - Advanced options mirror CLI flags but use friendly labels and help text.
            - Outputs remain deterministic. For reproducibility, copy the shown code snippet.
            """
        )


def _tab_single_pokemon(st: "object") -> None:  # pragma: no cover - UI only
    from pogo_analyzer.data.base_stats import load_default_base_stats
    from pogo_analyzer.formulas import effective_stats, infer_level_from_cp
    from pogo_analyzer.pve import ChargeMove, FastMove, compute_pve_score
    from pogo_analyzer.pvp import PvpChargeMove, PvpFastMove, compute_pvp_score

    st.header("Single Pokémon Quick Check")

    with st.form("quick_form", clear_on_submit=False):
        st.subheader("Basics")
        col1, col2 = st.columns(2)
        with col1:
            # Autocomplete via selectbox: type to filter list; press Enter to select
            repo = load_default_base_stats()
            options: list[str] = []
            display_to_query: dict[str, str] = {}
            for entry in repo:
                display = (entry.name or entry.slug).strip()
                if not display:
                    continue
                if display not in display_to_query:
                    display_to_query[display] = entry.name or entry.slug
                    options.append(display)
            options.sort(key=lambda s: s.lower())

            name_display = st.selectbox(
                "Pokémon name",
                options=options,
                index=None,
                placeholder="Start typing to search…",
                help="Type to filter; press Enter to pick.",
            )
            name = display_to_query.get(name_display or "", "")
            cp = st.number_input("Combat Power (CP)", min_value=0, value=0, step=1)
            iv_a = st.number_input("IV Attack", 0, 15, 15)
            iv_d = st.number_input("IV Defense", 0, 15, 15)
            iv_s = st.number_input("IV Stamina", 0, 15, 15)
        with col2:
            variant = st.radio(
                "Variant",
                options=["Normal", "Shadow", "Purified"],
                horizontal=True,
                help="Shadow and Purified are mutually exclusive."
            )
            shadow = variant == "Shadow"
            purified = variant == "Purified"
            lucky = st.checkbox(
                "Lucky (trade bonus)",
                disabled=shadow,
                help=(
                    "Lucky status comes from trading and cannot apply to Shadow Pokémon. "
                    "Purified and Normal can be Lucky."
                ),
            )
            best_buddy = st.checkbox("Best Buddy (+1 CPM level)")
            observed_hp = st.number_input("Observed HP (optional)", min_value=0, value=0, step=1)

        st.divider()
        st.subheader("Species / Base Stats")
        st.caption("Leave base stats empty to auto-resolve from dataset by name.")
        bs1, bs2, bs3 = st.columns(3)
        with bs1:
            base_a = st.number_input("Base Attack (optional)", min_value=0, value=0, step=1)
        with bs2:
            base_d = st.number_input("Base Defense (optional)", min_value=0, value=0, step=1)
        with bs3:
            base_s = st.number_input("Base Stamina (optional)", min_value=0, value=0, step=1)

        st.divider()
        st.subheader("PvE (optional)")
        pve_enabled = st.checkbox("Include PvE value", help="Compute rotation DPS/TDO and a combined PvE value.")
        if pve_enabled:
            pve_c1, pve_c2, pve_c3 = st.columns(3)
            with pve_c1:
                fast_name = st.text_input("Fast move name", value="Snarl")
                fast_power = st.number_input("Fast power", min_value=0.0, value=12.0)
                fast_energy = st.number_input("Fast energy gain", min_value=0.0, value=13.0)
                fast_dur = st.number_input("Fast duration (s)", min_value=0.1, value=1.0)
                fast_stab = st.checkbox("Fast STAB")
            with pve_c2:
                ch1_name = st.text_input("Charge 1 name", value="Brutal Swing")
                ch1_power = st.number_input("Charge 1 power", min_value=0.0, value=65.0)
                ch1_cost = st.number_input("Charge 1 energy cost", min_value=1.0, value=40.0)
                ch1_dur = st.number_input("Charge 1 duration (s)", min_value=0.1, value=1.9)
                ch1_stab = st.checkbox("Charge 1 STAB", value=True)
            with pve_c3:
                ch2_toggle = st.checkbox("Add Charge 2")
                ch2_name = st.text_input("Charge 2 name", value="", disabled=not ch2_toggle)
                ch2_power = st.number_input("Charge 2 power", min_value=0.0, value=110.0, disabled=not ch2_toggle)
                ch2_cost = st.number_input("Charge 2 energy cost", min_value=1.0, value=50.0, disabled=not ch2_toggle)
                ch2_dur = st.number_input("Charge 2 duration (s)", min_value=0.1, value=3.9, disabled=not ch2_toggle)
                ch2_stab = st.checkbox("Charge 2 STAB", value=False, disabled=not ch2_toggle)

            pve_adv = st.expander("PvE advanced")
            with pve_adv:
                target_def = st.number_input("Target Defense (boss)", min_value=1.0, value=180.0)
                incoming_dps = st.number_input("Incoming DPS (boss)", min_value=1.0, value=35.0)
                alpha = st.number_input("Alpha (DPS↔TDO blend)", min_value=0.01, max_value=0.99, value=0.6)
                e_from_dmg = st.number_input("Energy from damage ratio", min_value=0.0, value=0.0, help="Approx. 0.5 ≈ 1 energy per 2 HP lost.")
                relobby_phi = st.number_input("Relobby penalty (phi)", min_value=0.0, value=0.0, help="Use >0 to dampen builds that faint often.")

        st.divider()
        st.subheader("PvP (optional)")
        pvp_enabled = st.checkbox("Include PvP value", help="Compute Stat Product, Move Pressure, and a blended PvP score.")
        if pvp_enabled:
            pvp_c1, pvp_c2 = st.columns(2)
            with pvp_c1:
                league_cap = st.radio(
                    "League",
                    options=[1500, 2500, 0],
                    format_func=lambda v: "Great (1500)" if v==1500 else ("Ultra (2500)" if v==2500 else "Master (no cap)"),
                    index=0,
                    horizontal=True,
                )
                beta = st.number_input("Beta (SP↔MP blend)", min_value=0.01, max_value=0.99, value=0.52)
                shield_weights = st.text_input("Shield weights (w0,w1,w2)", value="")
            with pvp_c2:
                f_turns = st.number_input("Fast turns (PvP)", min_value=1, value=4)
                bait_prob = st.text_input("Bait prob or model (e.g., 0.55 or a=0.4,b=-0.1,c=0.35,d=0.0)", value="")
                sp_ref = st.number_input("SP reference (optional)", min_value=0.0, value=0.0)
                mp_ref = st.number_input("MP reference (optional)", min_value=0.0, value=0.0)

        submitted = st.form_submit_button("Run Quick Check")

    if not submitted:
        return

    if not name:
        st.error("Please enter a Pokémon name.")
        return

    # Resolve base stats
    repo = load_default_base_stats()
    if base_a and base_d and base_s:
        ba, bd, bs = int(base_a), int(base_d), int(base_s)
    else:
        try:
            entry = repo.get(name)
        except KeyError:
            st.error("Species not found in base stats. Provide base stats explicitly.")
            return
        ba, bd, bs = entry.attack, entry.defense, entry.stamina

    IVs = (int(iv_a), int(iv_d), int(iv_s))
    obs_hp = int(observed_hp) if observed_hp > 0 else None

    # Inference
    with st.spinner("Inferring level and computing stats…"):
        try:
            level, cpm = infer_level_from_cp(ba, bd, bs, *IVs, int(cp), is_shadow=shadow, is_best_buddy=best_buddy, observed_hp=obs_hp)
            A, D, H = effective_stats(ba, bd, bs, *IVs, level, is_shadow=shadow, is_best_buddy=best_buddy)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Level inference failed: {exc}")
            return

    st.success(f"Level {level:.1f} (CPM {cpm:.6f}) — A={A:.2f}, D={D:.2f}, H={H}")

    # PvE
    if pve_enabled:
        with st.spinner("Scoring PvE…"):
            try:
                fast = FastMove(fast_name, power=float(fast_power), energy_gain=float(fast_energy), duration=float(fast_dur), stab=bool(fast_stab))
                charges = [
                    ChargeMove(ch1_name, power=float(ch1_power), energy_cost=float(ch1_cost), duration=float(ch1_dur), stab=bool(ch1_stab))
                ]
                if ch2_toggle and ch2_name:
                    charges.append(ChargeMove(ch2_name, power=float(ch2_power), energy_cost=float(ch2_cost), duration=float(ch2_dur), stab=bool(ch2_stab)))

                pve = compute_pve_score(
                    A, D, int(H), fast, charges,
                    target_defense=float(target_def), incoming_dps=float(incoming_dps), alpha=float(alpha),
                    energy_from_damage_ratio=float(e_from_dmg), relobby_penalty=(float(relobby_phi) if relobby_phi>0 else None),
                )
                st.subheader("PvE value")
                st.metric("Rotation DPS", f"{pve['dps']:.2f}")
                st.metric("TDO", f"{pve['tdo']:.2f}")
                st.metric("PvE Value", f"{pve['value']:.2f}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"PvE evaluation failed: {exc}")

    # PvP
    if pvp_enabled:
        with st.spinner("Scoring PvP…"):
            try:
                sw = None
                if shield_weights.strip():
                    parts = [float(x.strip()) for x in shield_weights.split(',') if x.strip()]
                    if len(parts) == 3:
                        sw = parts
                bait_model = None
                bait_prob_val: float | None = None
                if bait_prob.strip():
                    if '=' in bait_prob:
                        # Parse a=,b=,c=,d=
                        bait_model = {}
                        for kv in bait_prob.split(','):
                            k, _, v = kv.partition('=')
                            bait_model[k.strip()] = float(v.strip())
                    else:
                        bait_prob_val = float(bait_prob)

                pvp = compute_pvp_score(
                    A, D, int(H),
                    PvpFastMove(name="fast", damage=float(fast_power), energy_gain=float(fast_energy), turns=int(f_turns)),
                    [PvpChargeMove(name=ch1_name, damage=float(ch1_power), energy_cost=float(ch1_cost))],
                    league="great" if league_cap==1500 else ("ultra" if league_cap==2500 else "master"),
                    beta=float(beta), stat_product_reference=(float(sp_ref) if sp_ref>0 else None),
                    move_pressure_reference=(float(mp_ref) if mp_ref>0 else None),
                    bait_probability=bait_prob_val, shield_weights=sw,
                )
                st.subheader("PvP value")
                st.metric("Stat Product (norm)", f"{pvp['stat_product_normalised']:.4f}")
                st.metric("Move Pressure (norm)", f"{pvp['move_pressure_normalised']:.4f}")
                st.metric("PvP Score", f"{pvp['score']:.4f}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"PvP evaluation failed: {exc}")


def _tab_pvp_scoreboard(st: "object") -> None:  # pragma: no cover - UI only
    import json
    import tempfile
    from pathlib import Path
    import pandas as pd
    try:
        import pvp_scoreboard_generator as psg  # available when installed
    except ModuleNotFoundError:
        # Fallback: load from source tree when running the GUI directly
        from importlib import util as _import_util
        _root = Path(__file__).resolve().parents[1] / "pvp_scoreboard_generator.py"
        if not _root.is_file():
            st.error(
                "pvp_scoreboard_generator module not found. Ensure you installed the package or run the GUI from the repo root."
            )
            return
        _spec = _import_util.spec_from_file_location("pvp_scoreboard_generator", str(_root))
        psg = _import_util.module_from_spec(_spec)  # type: ignore[assignment]
        assert _spec and _spec.loader
        _spec.loader.exec_module(psg)  # type: ignore[union-attr]

    st.header("PvP Scoreboard Helper")
    with st.form("pvp_form"):
        species = st.file_uploader("Normalized species JSON", type=["json"], accept_multiple_files=False)
        moves = st.file_uploader("Normalized moves JSON", type=["json"], accept_multiple_files=False)
        learnsets = st.file_uploader("Learnsets JSON", type=["json"], accept_multiple_files=False)
        league = st.selectbox("League", options=[1500, 2500, 0], format_func=lambda v: "Great (1500)" if v==1500 else ("Ultra (2500)" if v==2500 else "Master (no cap)"))
        iv_mode = st.selectbox("IV mode", options=["fixed","max-sp"], index=0)
        iv_floor = st.number_input("IV floor", min_value=0, max_value=15, value=0)
        submitted = st.form_submit_button("Generate")

    if not submitted or not (species and moves and learnsets):
        return

    tmpdir = Path(tempfile.mkdtemp(prefix="pogo_gui_"))
    sp_path = tmpdir / "species.json"; sp_path.write_bytes(species.getvalue())
    mv_path = tmpdir / "moves.json"; mv_path.write_bytes(moves.getvalue())
    ls_path = tmpdir / "learnsets.json"; ls_path.write_bytes(learnsets.getvalue())

    csv_path = psg.main([
        "--species", str(sp_path),
        "--moves", str(mv_path),
        "--learnsets", str(ls_path),
        "--league-cap", str(league),
        "--iv-mode", iv_mode,
        "--iv-floor", str(iv_floor),
    ])

    df = pd.read_csv(csv_path)
    st.dataframe(df.head(50))
    with open(csv_path, "rb") as f:
        st.download_button("Download CSV", data=f, file_name=csv_path.name, mime="text/csv")


def _tab_raid_scoreboard(st: "object") -> None:  # pragma: no cover - UI only
    import tempfile
    import pandas as pd
    import raid_scoreboard_generator as rsg

    st.header("Raid Scoreboard")
    st.caption("Generate the default raid investment scoreboard (CSV/Excel).")
    preview_n = st.number_input("Preview rows", min_value=5, max_value=50, value=10, step=1)
    run = st.button("Generate Raid Scoreboard")
    if not run:
        st.info("Adjust preview count and click Generate.")
        return
    with st.spinner("Generating raid scoreboard…"):
        tmpdir = tempfile.mkdtemp(prefix="pogo_gui_raid_")
        result = rsg.main(["--output-dir", tmpdir, "--preview-limit", str(int(preview_n))])
    if result is None:
        st.error("Failed to build scoreboard.")
        return
    df = result.table.reset_index() if hasattr(result.table, "reset_index") else result.table
    try:
        import pandas as _pd  # noqa:F401
        if hasattr(df, "to_pandas"):
            df = df.to_pandas()
    except Exception:
        pass
    st.dataframe(df.head(int(preview_n)))
    with open(result.csv_path, "rb") as f:
        st.download_button("Download CSV", data=f, file_name=result.csv_path.name, mime="text/csv")
    if result.excel_path and result.excel_written and result.excel_path.exists():
        with open(result.excel_path, "rb") as f:
            st.download_button("Download Excel", data=f, file_name=result.excel_path.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":  # pragma: no cover
    main([])

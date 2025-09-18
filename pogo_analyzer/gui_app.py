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

    tabs = st.tabs(["Quick Check", "Raid Scoreboard", "PvP Scoreboard", "Data & Config", "Glossary", "About"])

    with tabs[0]:
        _tab_single_pokemon(st)

    with tabs[1]:
        _tab_raid_scoreboard(st)

    with tabs[2]:
        _tab_pvp_scoreboard(st)

    with tabs[3]:
        _tab_data_and_config(st)

    with tabs[4]:
        _tab_glossary(st)

    with tabs[5]:
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
    from pogo_analyzer.scoring import calculate_iv_bonus, calculate_raid_score
    from pogo_analyzer.data.raid_entries import DEFAULT_RAID_ENTRIES as _DEFAULT_RAID_ENTRIES
    try:
        from pogo_analyzer.ui_helpers import pve_verdict, pvp_verdict
    except ModuleNotFoundError:
        # Fallback for dev runs where module import paths may be stale
        from importlib import util as _util
        from pathlib import Path as _Path
        _uh_path = _Path(__file__).with_name("ui_helpers.py")
        spec = _util.spec_from_file_location("pogo_analyzer.ui_helpers", str(_uh_path))
        _mod = _util.module_from_spec(spec)  # type: ignore[arg-type]
        assert spec and spec.loader
        spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        pve_verdict = _mod.pve_verdict  # type: ignore[attr-defined]
        pvp_verdict = _mod.pvp_verdict  # type: ignore[attr-defined]

    st.header("Single Pokémon Quick Check")

    # Caching & memoization for speed with version-compatible decorators
    def _get_cache_decorator(names: list[str]):
        for name in names:
            deco = getattr(st, name, None)
            if callable(deco):
                return deco
        # Fallback no-op decorator
        def _noop(*_args, **_kwargs):
            def _wrap(fn):
                return fn
            return _wrap
        return _noop

    _cache = _get_cache_decorator(["cache_data", "memo", "experimental_memo"])  # prefer stable APIs

    @_cache()
    def _base_stats_repo():
        return load_default_base_stats()

    @_cache()
    def _base_rating_lookup() -> dict[str, float]:
        table: dict[str, float] = {}
        for e in _DEFAULT_RAID_ENTRIES:
            key = (e.name or "").strip().lower()
            if key and key not in table:
                table[key] = float(e.base)
        return table

    @_cache()
    def _infer(ba: int, bd: int, bs: int, ivs: tuple[int, int, int], cp_val: int, shadow: bool, buddy: bool, obs_hp: int | None):
        level, cpm = infer_level_from_cp(ba, bd, bs, *ivs, int(cp_val), is_shadow=shadow, is_best_buddy=buddy, observed_hp=obs_hp)
        A, D, H = effective_stats(ba, bd, bs, *ivs, level, is_shadow=shadow, is_best_buddy=buddy)
        return level, cpm, A, D, H

    @st.cache_data(show_spinner=False)
    def _load_moves_db() -> dict:
        import json
        from pathlib import Path
        path = Path("normalized_data/normalized_moves.json")
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @st.cache_data(show_spinner=False)
    def _load_exclusives_db() -> dict:
        import json
        from pathlib import Path
        path = Path("normalized_data/exclusive_moves.json")
        if not path.is_file():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload.get("exclusives", {}) if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _lookup_move(db: dict, name: str) -> dict | None:
        if not db or not name:
            return None
        for bucket in ("fast", "charge"):
            for m in db.get(bucket, []):
                if m.get("name") == name:
                    return m
        low = name.lower()
        for bucket in ("fast", "charge"):
            for m in db.get(bucket, []):
                if str(m.get("name", "")).lower() == low:
                    return m
        return None

    with st.form("quick_form", clear_on_submit=False):
        st.subheader("Basics")
        col1, col2 = st.columns(2)
        with col1:
            # Autocomplete via selectbox: type to filter list; press Enter to select
            repo = _base_stats_repo()
            options: list[str] = []
            display_to_query: dict[str, str] = {}

            def _include_in_selector(entry) -> bool:
                slug = (entry.slug or "").strip().lower()
                name = (entry.name or entry.slug or "").strip().lower()
                tags = {t.strip().lower() for t in (entry.tags or ())}
                # Exclude Mega and Shadow/Purified forms from the dropdown; radio controls variant
                if "_mega" in slug or "mega" in tags or "(mega" in name:
                    return False
                if slug.startswith("shadow_") or "shadow" in tags or "(shadow" in name:
                    return False
                if slug.startswith("purified_") or "purified" in tags or "(purified" in name:
                    return False
                return True

            for entry in repo:
                if not _include_in_selector(entry):
                    continue
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
            target_cp = st.number_input("Target CP (optional)", min_value=0, value=0, step=1, help="Personal build target to flag underpowered status.")
            iv_a = st.number_input("IV Attack", 0, 15, 15)
            iv_d = st.number_input("IV Defense", 0, 15, 15)
            iv_s = st.number_input("IV Stamina", 0, 15, 15)
        with col2:
            # Variant first to drive Lucky disabled state
            variant = st.radio(
                "Variant",
                options=["Normal", "Shadow", "Purified"],
                horizontal=True,
                help="Shadow and Purified are mutually exclusive.",
            )
            shadow = variant == "Shadow"
            purified = variant == "Purified"

            # Lucky and Best Buddy matter; Lucky is not applicable to Shadow
            lucky = st.checkbox(
                "Lucky (trade bonus)",
                disabled=shadow,
                help=(
                    "Lucky status comes from trading and cannot apply to Shadow Pokémon. "
                    "Purified and Normal can be Lucky."
                ),
            )
            if shadow:
                lucky = False
            best_buddy = st.checkbox("Best Buddy (+1 CPM level)")
            observed_hp = st.number_input("Observed HP (optional)", min_value=0, value=0, step=1)
            # Always evaluate best moves and mega availability automatically
            note = st.text_input("Notes (optional)", value="")

            # Hint when the selected species' family has a Mega form
            try:
                repo = _base_stats_repo()
                if name:
                    e = repo.get(name)
                    fam_val = e.family.get("id") if isinstance(e.family, dict) else e.family
                    has_mega = False
                    if fam_val:
                        fam_val = str(fam_val)
                        for cand in repo:
                            cf = cand.family.get("id") if isinstance(cand.family, dict) else cand.family
                            if (str(cf) == fam_val) and (
                                ("_mega" in cand.slug.lower())
                                or ("mega" in [t.lower() for t in cand.tags])
                                or ((cand.name or "").lower().find("mega") >= 0)
                            ):
                                has_mega = True
                                break
                    if has_mega:
                        st.caption("Family has a Mega form — both scores will be shown.")
            except Exception:
                pass

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
                fast_name = st.text_input("Fast move name", value="")
                fast_power = st.number_input("Fast power", min_value=0.0, value=0.0)
                fast_energy = st.number_input("Fast energy gain", min_value=0.0, value=0.0)
                fast_dur = st.number_input("Fast duration (s)", min_value=0.1, value=1.0)
                fast_stab = st.checkbox("Fast STAB")
            with pve_c2:
                ch1_name = st.text_input("Charge 1 name", value="")
                ch1_power = st.number_input("Charge 1 power", min_value=0.0, value=0.0)
                ch1_cost = st.number_input("Charge 1 energy cost", min_value=1.0, value=1.0)
                ch1_dur = st.number_input("Charge 1 duration (s)", min_value=0.1, value=1.0)
                ch1_stab = st.checkbox("Charge 1 STAB", value=False)
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
                boss_types = st.multiselect(
                    "Boss type(s)",
                    options=[
                        "Normal","Fire","Water","Grass","Electric","Ice","Fighting","Poison","Ground","Flying",
                        "Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy",
                    ],
                    default=["Psychic"],
                    help="Apply type effectiveness (1.6×/0.625×) based on your move types.",
                )

            # Optional move type selectors (used to apply type effectiveness vs boss types)
            fast_type = st.selectbox(
                "Fast move type (optional)",
                [
                    "",
                    "Normal","Fire","Water","Grass","Electric","Ice","Fighting","Poison","Ground","Flying",
                    "Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy",
                ],
                index=0,
            )
            ch1_type = st.selectbox(
                "Charge 1 type (optional)",
                [
                    "",
                    "Normal","Fire","Water","Grass","Electric","Ice","Fighting","Poison","Ground","Flying",
                    "Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy",
                ],
                index=0,
            )
            if ch2_toggle and ch2_name:
                ch2_type = st.selectbox(
                    "Charge 2 type (optional)",
                    [
                        "",
                        "Normal","Fire","Water","Grass","Electric","Ice","Fighting","Poison","Ground","Flying",
                        "Psychic","Bug","Rock","Ghost","Dragon","Dark","Steel","Fairy",
                    ],
                    index=0,
                )

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

        # Recommended moves autofill (best-known defaults per species)
        rec_enable = st.checkbox("Use recommended moves (auto)", value=True, help="Autofill best-known PvE/PvP moves for the selected Pokémon.")
        if rec_enable and name:
            try:
                from pogo_analyzer.data.move_guidance import normalise_name
            except Exception:
                normalise_name = lambda x: (x or "").strip().lower().replace(" ", "-")  # fallback
            key = normalise_name(name)
            # Minimal built-in recommendations; extend as needed
            if key == "gengar":
                # PvE best: Shadow Claw + Shadow Ball (STAB)
                fast_name = fast_name or "Shadow Claw"
                if fast_power == 0.0:
                    fast_power = 9.0
                if fast_energy == 0.0:
                    fast_energy = 6.0
                fast_dur = fast_dur or 0.7
                fast_stab = True
                if not fast_type:
                    fast_type = "Ghost"

                ch1_name = ch1_name or "Shadow Ball"
                if ch1_power == 0.0:
                    ch1_power = 100.0
                if ch1_cost <= 1.0:
                    ch1_cost = 50.0
                ch1_dur = ch1_dur or 3.0
                ch1_stab = True
                if not ch1_type:
                    ch1_type = "Ghost"

                # PvP: Shadow Claw + Shadow Ball (typical stats)
                if pvp_enabled:
                    f_turns = max(1, f_turns or 2)
                    # These are PvP stats for Shadow Claw
                    fast_power = fast_power or 3.0
                    fast_energy = fast_energy or 8.0

        submitted = st.form_submit_button("Run Quick Check")

    if not submitted:
        return

    if not name:
        st.error("Please enter a Pokémon name.")
        return

    # Resolve base stats
    repo = _base_stats_repo()
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
            level, cpm, A, D, H = _infer(ba, bd, bs, IVs, int(cp), shadow, best_buddy, obs_hp)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Level inference failed: {exc}")
            return

    st.success(f"Level {level:.1f} (CPM {cpm:.6f}) — A={A:.2f}, D={D:.2f}, H={H}")

    # Helper: badges and result card
    def badge(label: str) -> None:
        st.markdown(f'<span class="badge">{label}</span>', unsafe_allow_html=True)

    def result_card(title: str, fields: dict[str, str], flags: dict[str, bool]) -> None:
        st.markdown('<div class="card section">', unsafe_allow_html=True)
        st.subheader(title)
        c1, c2, c3 = st.columns(3)
        cols = (c1, c2, c3)
        for i, (k, v) in enumerate(fields.items()):
            cols[i % 3].metric(k, v)
        st.write("Badges:")
        any_flag = False
        for key, enabled in flags.items():
            if enabled:
                any_flag = True
                badge(key)
        if not any_flag:
            st.caption("No special statuses")
        st.markdown("</div>", unsafe_allow_html=True)

    # Present core results in a card with badges
    result_card(
        f"{name} — Quick Check",
        {
            "Level": f"{level:.1f}",
            "CPM": f"{cpm:.6f}",
            "Attack": f"{A:.2f}",
            "Defense": f"{D:.2f}",
            "HP": f"{H:d}",
        },
        {"Shadow": shadow, "Purified": purified, "Lucky": bool(lucky), "Best Buddy": bool(best_buddy)},
    )

    # Helper: auto-detect ETM/CD requirement
    def _auto_needs_tm(species_label: str) -> tuple[bool | None, str]:
        try:
            from pogo_analyzer.data.move_guidance import get_move_guidance
        except Exception:
            get_move_guidance = None  # type: ignore[assignment]
        # Primary: curated guidance
        if get_move_guidance is not None:
            g = get_move_guidance(species_label)
            if g and g.needs_tm:
                return True, g.note
        # Secondary: exclusives DB (from gamemaster import)
        ex = _load_exclusives_db()
        spec_keys = (species_label, species_label.title(), species_label.lower())
        for k in spec_keys:
            if k in ex:
                info = ex[k] or {}
                # If species has any exclusive fast/charge, mark as maybe
                if (info.get("fast") or info.get("charge")):
                    return None, "Species has legacy/elite moves; specific requirement varies."
        return False, ""

    def _mega_flags(species_label: str) -> tuple[bool, bool]:
        """Detect whether a species (or its family) has a Mega form.

        Returns (mega_now_or_exists, mega_soon_from_curated).
        """
        mega_presence = False
        try:
            repo = _base_stats_repo()
            entry = repo.get(species_label)
            fam_val = entry.family.get("id") if isinstance(entry.family, dict) else entry.family
            if fam_val:
                fam_val = str(fam_val)
                for cand in repo:
                    cf = cand.family.get("id") if isinstance(cand.family, dict) else cand.family
                    if (str(cf) == fam_val) and (
                        ("_mega" in cand.slug.lower())
                        or ("mega" in [t.lower() for t in cand.tags])
                        or ((cand.name or "").lower().find("mega") >= 0)
                    ):
                        mega_presence = True
                        break
        except Exception:
            pass

        mega_now_cur = False
        mega_soon = False
        try:
            from pogo_analyzer.data.raid_entries import DEFAULT_RAID_ENTRIES as _ENTRIES
            s = (species_label or "").strip().lower()
            for e in _ENTRIES:
                if e.name.strip().lower() == s:
                    mega_now_cur = mega_now_cur or bool(getattr(e, "mega_now", False))
                    mega_soon = mega_soon or bool(getattr(e, "mega_soon", False))
        except Exception:
            pass

        mega_now = mega_now_cur or mega_presence
        return bool(mega_now), bool(mega_soon)

    # Overall Raid Score snapshot with simple tier and action chips
    try:
        base_table = _base_rating_lookup()
        base_rating = base_table.get((name or "").strip().lower(), 70.0)
        ivb = calculate_iv_bonus(int(iv_a), int(iv_d), int(iv_s))
        needs_tm_auto, needs_tm_note = _auto_needs_tm(name)
        mega_now_flag, mega_soon_flag = _mega_flags(name)
        # Best-case baseline: do not penalize for exclusives; evaluate without mega
        _rs_base = calculate_raid_score(
            float(base_rating), float(ivb), lucky=bool(lucky), needs_tm=False, mega_bonus_now=False, mega_bonus_soon=False
        )
        # With mega: apply whichever flag is available; else N/A
        _rs_mega = None
        if mega_now_flag or mega_soon_flag:
            _rs_mega = calculate_raid_score(
                float(base_rating), float(ivb), lucky=bool(lucky), needs_tm=False,
                mega_bonus_now=bool(mega_now_flag), mega_bonus_soon=bool(mega_soon_flag)
            )

        def _apply_personal_bonuses(x: float | None) -> float | None:
            if x is None:
                return None
            if purified:
                x += 1
            if best_buddy:
                x += 2
            return max(1.0, min(100.0, round(float(x), 1)))

        _rs_base = _apply_personal_bonuses(_rs_base)
        _rs_mega = _apply_personal_bonuses(_rs_mega)
        def _tier(x: float) -> str:
            if x >= 90:
                return "S"
            if x >= 85:
                return "A"
            if x >= 78:
                return "B"
            if x >= 70:
                return "C"
            return "D"
        _tier_letter = _tier(_rs_base)
        st.subheader("Raid Score (Best Moves)")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("No Mega", f"{_rs_base:.1f}")
        with m2:
            st.metric("With Mega" + (" (est)" if (_rs_mega is None) else ""), ("N/A" if _rs_mega is None else f"{_rs_mega:.1f}"))

        st.caption(f"Tier (no mega): {_tier_letter}")
        m3 = st.container()
        with m3:
            chips: list[str] = []
            _targ = locals().get("target_cp", 0) or 0
            _cpv = locals().get("cp", 0) or 0
            # Auto ETM/CD chip (note: score is best-case, no penalty applied)
            if needs_tm_auto is True:
                chips.append("Needs Elite TM")
            if _targ and _cpv and _cpv < _targ:
                chips.append("Under target CP")
            if _tier_letter in {"S", "A", "B"}:
                chips.append("Worth building now")
            if chips:
                st.markdown(" ".join(f"<span class='badge'>{c}</span>" for c in chips), unsafe_allow_html=True)
        if needs_tm_note:
            st.caption(needs_tm_note)
        # Mega commentary
        if _rs_mega is not None:
            delta = float(_rs_mega) - float(_rs_base)
            if delta >= 2.0:
                st.caption("This Pokémon ranks higher with its Mega evolution due to strong raid utility.")
            elif delta >= 0.5:
                st.caption("Mega evolution provides a modest bump to the raid score.")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Raid score snapshot unavailable: {exc}")

    # PvE
    if pve_enabled:
        with st.spinner("Scoring PvE…"):
            try:
                def _se_multiplier(move_type: str, boss_types_list: list[str]) -> float:
                    mt = (move_type or "").strip().lower()
                    bts = {t.strip().lower() for t in (boss_types_list or [])}
                    super_eff = {
                        "ghost": {"psychic","ghost"},
                        "dark": {"psychic","ghost"},
                        "rock": {"fire","ice","flying","bug"},
                        "ground": {"fire","electric","poison","rock","steel"},
                        "fighting": {"normal","ice","rock","dark","steel"},
                        "bug": {"grass","psychic","dark"},
                        "grass": {"water","ground","rock"},
                        "water": {"fire","ground","rock"},
                        "fire": {"grass","ice","bug","steel"},
                        "electric": {"water","flying"},
                        "ice": {"grass","ground","flying","dragon"},
                        "steel": {"ice","rock","fairy"},
                        "fairy": {"fighting","dragon","dark"},
                        "dragon": {"dragon"},
                        "poison": {"grass","fairy"},
                        "flying": {"grass","fighting","bug"},
                        "psychic": {"fighting","poison"},
                    }
                    resisted = {
                        "ghost": {"dark"},
                        "dark": {"fighting","dark","fairy"},
                        "rock": {"fighting","ground","steel"},
                        "ground": {"grass","bug"},
                        "fighting": {"flying","poison","psychic","bug","fairy"},
                        "bug": {"fighting","flying","poison","ghost","steel","fire","fairy"},
                        "grass": {"flying","poison","bug","steel","fire","dragon"},
                        "water": {"water","grass","dragon"},
                        "fire": {"fire","water","rock","dragon"},
                        "electric": {"grass","electric","dragon","ground"},
                        "ice": {"fire","water","ice","steel"},
                        "steel": {"fire","water","electric","steel"},
                        "fairy": {"poison","steel","fire"},
                        "dragon": {"steel"},
                        "poison": {"poison","ground","rock","ghost"},
                        "flying": {"electric","rock","steel"},
                        "psychic": {"psychic","steel"},
                    }
                    if mt and any(t in super_eff.get(mt, set()) for t in bts):
                        return 1.6
                    if mt and any(t in resisted.get(mt, set()) for t in bts):
                        return 0.625
                    return 1.0

                fast = FastMove(
                    fast_name,
                    power=float(fast_power),
                    energy_gain=float(fast_energy),
                    duration=float(fast_dur),
                    stab=bool(fast_stab),
                    type_effectiveness=_se_multiplier(fast_type, boss_types if 'boss_types' in locals() else []),
                )
                charges = [
                    ChargeMove(
                        ch1_name,
                        power=float(ch1_power),
                        energy_cost=float(ch1_cost),
                        duration=float(ch1_dur),
                        stab=bool(ch1_stab),
                        type_effectiveness=_se_multiplier(ch1_type, boss_types if 'boss_types' in locals() else []),
                    )
                ]
                if ch2_toggle and ch2_name:
                    eff2 = _se_multiplier(locals().get('ch2_type', ''), boss_types if 'boss_types' in locals() else [])
                    charges.append(ChargeMove(ch2_name, power=float(ch2_power), energy_cost=float(ch2_cost), duration=float(ch2_dur), stab=bool(ch2_stab), type_effectiveness=eff2))

                pve = compute_pve_score(
                    A, D, int(H), fast, charges,
                    target_defense=float(target_def), incoming_dps=float(incoming_dps), alpha=float(alpha),
                    energy_from_damage_ratio=float(e_from_dmg), relobby_penalty=(float(relobby_phi) if relobby_phi>0 else None),
                )
                st.subheader("PvE value")
                st.metric("Rotation DPS", f"{pve['dps']:.2f}")
                st.metric("TDO", f"{pve['tdo']:.2f}")
                st.metric("PvE Value", f"{pve['value']:.2f}")
                label, advice = pve_verdict(float(pve["dps"]), float(pve["tdo"]))
                st.info(f"PvE verdict: {label} — {advice}")
                tier, action = __import__("pogo_analyzer").pve_tier(float(pve["dps"]), float(pve["tdo"]))
                st.markdown(f"**Recommendation:** <span class='badge'>{action}</span> · Tier <span class='badge'>{tier}</span>", unsafe_allow_html=True)
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
                vp_label, vp_advice = pvp_verdict(float(pvp["score"]))
                st.info(f"PvP verdict: {vp_label} — {vp_advice}")
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
    st.dataframe(df.head(50), use_container_width=True)
    with open(csv_path, "rb") as f:
        st.download_button("Download CSV", data=f, file_name=csv_path.name, mime="text/csv")


def _tab_raid_scoreboard(st: "object") -> None:  # pragma: no cover - UI only
    import tempfile
    import pandas as pd
    import raid_scoreboard_generator as rsg

    st.header("Raid Scoreboard")
    st.caption("Generate the raid investment scoreboard and filter it inline. Defaults mirror CLI behavior.")

    # Top controls
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    with c1:
        preview_n = st.number_input("Preview rows", min_value=5, max_value=100, value=25, step=1)
    with c2:
        density = st.radio("Row density", options=["Cozy", "Compact"], horizontal=True, index=0)
    with c3:
        score_min, score_max = st.slider("Score range", min_value=1, max_value=100, value=(70, 100))
    with c4:
        needs_tm_filter = st.selectbox("Needs Special Move?", options=["Any", "Yes", "No"], index=0)

    run = st.button("Generate Raid Scoreboard")
    if not run:
        st.info("Adjust filters and click Generate.")
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

    # Filters
    if "Raid Score (1-100)" in df.columns:
        df = df[(df["Raid Score (1-100)"] >= score_min) & (df["Raid Score (1-100)"] <= score_max)]
    if needs_tm_filter != "Any" and "Move Needs (CD/ETM?)" in df.columns:
        df = df[df["Move Needs (CD/ETM?)"] == ("Yes" if needs_tm_filter == "Yes" else "No")]

    # Side filters
    left, right = st.columns([1, 2])
    with left:
        role_vals = sorted(set(df.get("Primary Role", []))) if "Primary Role" in df.columns else []
        role = st.selectbox("Role", options=["Any"] + role_vals if role_vals else ["Any"], index=0)
        if role != "Any" and "Primary Role" in df.columns:
            df = df[df["Primary Role"] == role]
        search = st.text_input("Search name", value="")
        if search.strip() and "Your Pokémon" in df.columns:
            q = search.strip().lower()
            df = df[df["Your Pokémon"].str.lower().str.contains(q)]
        st.caption(f"{len(df)} rows after filters")

    with right:
        cfg = None
        try:
            cfg = {
                "Raid Score (1-100)": st.column_config.ProgressColumn(
                    "Raid Score", min_value=1, max_value=100, help="Higher is better"
                )
            }
        except Exception:
            cfg = None
        height = 520 if density == "Cozy" else 380
        st.dataframe(df.head(int(preview_n)), use_container_width=True, height=height, column_config=cfg)

        # Selection + export
        names = list(df["Your Pokémon"]) if "Your Pokémon" in df.columns else []
        selected = st.multiselect("Select rows to export", options=names)
        if selected:
            sel_df = df[df["Your Pokémon"].isin(selected)]
            csv_bytes = sel_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download selected (CSV)", data=csv_bytes, file_name="raid_scoreboard_selected.csv", mime="text/csv")

        # Full exports produced by generator
        with open(result.csv_path, "rb") as f:
            st.download_button("Download full CSV", data=f, file_name=result.csv_path.name, mime="text/csv")
        if result.excel_path and result.excel_written and result.excel_path.exists():
            with open(result.excel_path, "rb") as f:
                st.download_button(
                    "Download full Excel",
                    data=f,
                    file_name=result.excel_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )


def _tab_data_and_config(st: "object") -> None:  # pragma: no cover - UI only
    import os
    st.header("Data Refresh & Config")
    st.caption("Adjust scoreboard export defaults (session only) and manage normalized datasets.")

    with st.form("cfg_form"):
        out_dir = st.text_input("RAID_SCOREBOARD_OUTPUT_DIR", os.environ.get("RAID_SCOREBOARD_OUTPUT_DIR", ""))
        csv_name = st.text_input("RAID_SCOREBOARD_CSV", os.environ.get("RAID_SCOREBOARD_CSV", "raid_scoreboard.csv"))
        xlsx_name = st.text_input("RAID_SCOREBOARD_EXCEL", os.environ.get("RAID_SCOREBOARD_EXCEL", "raid_scoreboard.xlsx"))
        preview = st.number_input("RAID_SCOREBOARD_PREVIEW_LIMIT", min_value=5, max_value=100, value=int(os.environ.get("RAID_SCOREBOARD_PREVIEW_LIMIT", 10) or 10))
        enhanced = st.checkbox("Enhanced defaults (single check only)", value=False, help="Opt-in PvE/PvP defaults; does not change CSV exports.")
        submitted = st.form_submit_button("Apply")
    if submitted:
        if out_dir:
            os.environ["RAID_SCOREBOARD_OUTPUT_DIR"] = out_dir
        if csv_name:
            os.environ["RAID_SCOREBOARD_CSV"] = csv_name
        if xlsx_name:
            os.environ["RAID_SCOREBOARD_EXCEL"] = xlsx_name
        os.environ["RAID_SCOREBOARD_PREVIEW_LIMIT"] = str(int(preview))
        st.success("Configuration applied for this session.")


def _tab_glossary(st: "object") -> None:  # pragma: no cover - UI only
    st.header("Glossary")
    st.caption("Common terms and abbreviations used across the app.")

    entries: list[tuple[str, str]] = [
        ("α (alpha)", "PvE blend weight between DPS and TDO in the PvE value (default 0.60). Higher α favors glass‑cannon damage over durability."),
        ("β (beta)", "PvP blend weight between SP (bulk) and MP (offense) in the PvP score (default 0.52). Higher β favors bulk."),
        ("Bait (PvP)", "Throwing a cheaper charged move to draw shields; we blend a baited pair into Move Pressure so nukes matter with shields."),
        ("Best Buddy (BB)", "Friendship bonus that applies the CPM of +1 level at your current level (capped by CPM table). Increases A/D/H."),
        ("Best moves (auto)", "When ON, the app reads imported learnsets and picks strong PvE and PvP moves automatically; no typing needed."),
        ("CMP (PvP)", "Charge‑Move Priority (initiative). If both sides press at once, the higher current Attack acts first; we model a small bonus."),
        ("CP", "Combat Power. An in‑game summary number; we use CP only to infer level/CPM, not for scoring directly."),
        ("CPM", "Combat Power Multiplier. Scales base+IV stats by level: A = (A_base+IV)×CPM. BB applies CPM at L+1 (if available)."),
        ("DPS", "Damage per second in PvE. Average damage of your best energy‑feasible rotation. Higher is better; use with TDO."),
        ("DPT/EPT (PvP)", "Damage/Energy per turn for fast moves (turn = 0.5s). DPT reflects pressure; EPT drives charged move timing."),
        ("EHP", "Effective HP in PvE: HP × (Defense / TargetDefense). Proxy for how long you last against a boss."),
        ("GL/UL/ML", "Great/Ultra/Master Leagues: 1500 / 2500 / no CP cap. We can also optimize IVs for SP‑max under these caps."),
        ("Gamemaster", "PvPoke's public dataset (GitHub JSON) with species, moves, learnsets. We import it to enable auto best‑move selection."),
        ("IV", "Individual Values (0–15) added to base stats per Pokémon. Great for tie‑breakers/IV floors but moves & matchups matter more."),
        ("IV optimisation (PvP)", "Exact frontier search that finds the IVs and level giving maximum Stat Product under the league CP cap."),
        ("Learnset", "Legal fast/charge moves per species. We use this to pick best PvE/PvP moves without manual input."),
        ("MP (PvP)", "Move Pressure: fast pressure + best single charged (or baited pair), normalised per league to a 0–1 scale."),
        ("PvE", "Raids/Gyms. We compute Rotation DPS, TDO, and a blended PvE Value; we also provide a letter Tier and Build/Consider/Skip."),
        ("PvP", "Trainer battles. We compute a 0–1 PvP score from normalized SP (bulk) and normalized MP (offense)."),
        ("Relobby penalty (PvE)", "Dampens PvE Value to model downtime after faints/switches: multiply by exp(−φ × TDO)."),
        ("SE / Resisted", "Type effectiveness vs the boss: 1.6× super‑effective, 0.625× resisted. Applied per move; supports dual types."),
        ("SP (PvP)", "Stat Product = Attack × Defense × HP after level (and BB). Bulkier spreads have higher SP; optimized for league caps."),
        ("SP‑max (PvP)", "The maximum Stat Product reachable under a league cap by choosing optimal IVs and level (our optimizer finds this)."),
        ("STAB", "Same‑Type Attack Bonus. If a move matches your type, PvE damage gets a 1.2× multiplier; PvP logic also values typing."),
        ("TDO", "Total Damage Output in PvE = DPS × Time‑to‑Faint. High DPS with decent TDO is great; low TDO is a glass‑cannon profile."),
        ("TTF", "Time‑to‑Faint = EHP ÷ incoming DPS from the boss. Longer TTF means more total damage before fainting."),
        ("Type effectiveness", "How move type interacts with target types. We use 1.6× for super‑effective and 0.625× for resisted hits."),
        ("Tier (S/A/B/C/D/E/F)", "PvE letter tier + action: Build (S/A/B), Consider (C/D), Skip (E/F). Based on DPS & TDO bands (context‑aware)."),
    ]
    # Alphabetise by term for easier scanning
    entries = sorted(entries, key=lambda e: e[0].lower())

    q = st.text_input("Filter terms", placeholder="Type to filter (e.g., DPS, STAB, SP)…")
    ql = (q or "").strip().lower()
    filtered = [e for e in entries if ql in e[0].lower() or ql in e[1].lower()]
    filtered.sort(key=lambda e: e[0].lower())
    if not filtered:
        st.info("No matching terms. Try a different keyword.")
        return

    # Render in two columns for scanability
    left, right = st.columns(2)
    for i, (term, desc) in enumerate(filtered):
        col = left if i % 2 == 0 else right
        with col:
            st.markdown(f"**{term}** — {desc}")

if __name__ == "__main__":  # pragma: no cover
    main([])

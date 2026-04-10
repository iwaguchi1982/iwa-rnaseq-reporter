import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Optional, Any, Tuple

from iwa_rnaseq_reporter.legacy.analysis import (
    build_analysis_sample_table,
    add_display_labels,
)
from iwa_rnaseq_reporter.legacy.deg_input import (
    get_comparison_candidate_columns,
    summarize_groups,
    build_deg_input,
    validate_deg_input,
    build_comparison_sample_table,
)
from iwa_rnaseq_reporter.legacy.deg_stats import (
    compute_statistical_deg,
)
from iwa_rnaseq_reporter.legacy.ui_utils import (
    format_display_df,
)
from iwa_rnaseq_reporter.app.analysis_workspace_context import AnalysisWorkspaceContext
from iwa_rnaseq_reporter.app.deg_result_builder import build_deg_result_context
from iwa_rnaseq_reporter.app.deg_export_builder import build_deg_export_payload
from iwa_rnaseq_reporter.app.deg_export_bundle import (
    build_deg_export_bundle,
    build_deg_export_bundle_filename
)
from iwa_rnaseq_reporter.app.deg_handoff_builder import build_deg_handoff_payload
from iwa_rnaseq_reporter.app.comparison_portfolio_builder import (
    build_comparison_record,
    upsert_comparison_record,
    list_comparison_records,
    get_comparison_record
)
from iwa_rnaseq_reporter.app.comparison_portfolio_summary import (
    build_comparison_portfolio_summary_rows,
    build_comparison_portfolio_summary_dataframe
)
from iwa_rnaseq_reporter.app.comparison_portfolio_export_builder import (
    build_comparison_portfolio_export_bundle,
    build_comparison_portfolio_bundle_filename,
    build_comparison_portfolio_export_payload
)
from iwa_rnaseq_reporter.app.comparison_portfolio_handoff_builder import (
    build_comparison_portfolio_handoff_payload
)


def render_deg_comparison_design_section(
    workspace: AnalysisWorkspaceContext
) -> Tuple[Optional[Any], Optional[str], Optional[str], Optional[str]]:
    """
    Render Section 13: DEG Comparison Design.
    
    Returns:
        (deg_input_obj, comparison_column, group_a, group_b)
    """
    st.header("13. DEG Comparison Design")

    st.info(
        f"Comparison design uses the current analysis matrix and included samples.  \n"
        f"**Current Settings:** `{workspace.matrix_kind}` / `log2p1={workspace.analysis_config.log2p1}` / "
        f"`use_exclude={workspace.analysis_config.use_exclude}` / "
        f"`min_nonzero={workspace.analysis_config.min_feature_nonzero_samples}` / "
        f"`min_mean={workspace.analysis_config.min_feature_mean}`"
    )

    comparison_sample_table = build_analysis_sample_table(
        workspace.dataset,
        matrix_kind=workspace.matrix_kind,
        use_exclude=workspace.analysis_config.use_exclude,
    )

    # In v0.1.4, candidate columns are explicitly derived from included samples
    comparison_candidate_columns = get_comparison_candidate_columns(comparison_sample_table)

    if not comparison_candidate_columns:
        st.warning("No comparison-ready metadata columns were found among the currently included samples.")
        return None, None, None, None

    d1, d2, d3 = st.columns(3)
    with d1:
        comparison_column = st.selectbox(
            "Comparison column",
            options=comparison_candidate_columns,
            index=0,
            key="deg_comparison_col"
        )

    group_summary = summarize_groups(comparison_sample_table, comparison_column)
    valid_group_names = group_summary["group_name"].tolist()

    if len(valid_group_names) < 2:
        st.warning(
            f"Selected column '{comparison_column}' does not have at least 2 non-empty groups "
            "in the current analysis set."
        )
        return None, comparison_column, None, None

    with d2:
        group_a = st.selectbox(
            "Group A (Case)",
            options=valid_group_names,
            index=0,
            key="deg_group_a"
        )

    remaining_groups = [g for g in valid_group_names if g != group_a]
    with d3:
        group_b = st.selectbox(
            "Group B (Control)",
            options=remaining_groups,
            index=0 if remaining_groups else None,
            key="deg_group_b"
        )

    st.subheader("Group Summary (Included Samples)")
    st.dataframe(format_display_df(group_summary), use_container_width=True)

    try:
        deg_input_obj = build_deg_input(
            workspace.dataset,
            matrix_kind=workspace.matrix_kind,
            group_column=comparison_column,
            group_a=group_a,
            group_b=group_b,
            log2p1=workspace.analysis_config.log2p1,
            use_exclude=workspace.analysis_config.use_exclude,
            min_feature_nonzero_samples=workspace.analysis_config.min_feature_nonzero_samples,
            min_feature_mean=workspace.analysis_config.min_feature_mean,
        )

        issues = validate_deg_input(deg_input_obj, min_samples_per_group=2)

        st.write(
            f"**Comparison samples:** `{len(deg_input_obj.feature_matrix.columns)}` "
            f"(`{group_a}`: {len(deg_input_obj.group_a_samples)}, "
            f"`{group_b}`: {len(deg_input_obj.group_b_samples)})"
        )

        if issues:
            st.warning("Comparison design has validation issues:")
            for issue in issues:
                st.warning(issue)
        else:
            st.success("Comparison design looks ready for DEG preview.")

        with st.expander("Comparison Sample Table", expanded=False):
            st.dataframe(
                format_display_df(build_comparison_sample_table(deg_input_obj)),
                use_container_width=True,
            )
        
        return deg_input_obj, comparison_column, group_a, group_b

    except Exception as e:
        st.error(f"Failed to build comparison design: {e}")
        return None, comparison_column, group_a, group_b


def render_deg_analysis_section(
    workspace: AnalysisWorkspaceContext,
    deg_input_obj: Optional[Any],
    comparison_column: Optional[str],
    group_a: Optional[str],
    group_b: Optional[str],
):
    """
    Render Section 14: DEG Analysis (Statistical).
    """
    st.header("14. DEG Analysis")

    if deg_input_obj is not None:
        st.subheader("Comparison Summary")
        st.markdown(
            f"- **Comparison**: `{comparison_column}` (`{group_a}` vs `{group_b}`)\n"
            f"- **Samples**: {group_a} (`{len(deg_input_obj.group_a_samples)}`), {group_b} (`{len(deg_input_obj.group_b_samples)}`)\n"
            f"- **Data**: `{workspace.matrix_kind}` (log2p1: `{workspace.analysis_config.log2p1}`, exclude: `{workspace.analysis_config.use_exclude}`, min_nonzero: `{workspace.analysis_config.min_feature_nonzero_samples}`, min_mean: `{workspace.analysis_config.min_feature_mean}`)"
        )

        if st.button("▶ Run DEG", type="primary"):
            with st.spinner("Computing DEG..."):
                try:
                    st.session_state.deg_res = compute_statistical_deg(deg_input_obj)
                except Exception as e:
                    st.error(f"Failed to run DEG analysis: {e}")

        if "deg_res" in st.session_state:
            try:
                sort_options = [
                    "padj", "p_value", "abs_log2_fc", "log2_fc", "display_label", 
                    "gene_symbol", "mean_group_a", "mean_group_b", "feature_id"
                ]
                
                p1, p2, p3, p4 = st.columns(4)
                with p1:
                    p_thresh = st.number_input("P-value threshold (padj)", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
                with p2:
                    fc_thresh = st.number_input("|log2 FC| threshold", min_value=0.0, max_value=10.0, value=1.0, step=0.1)
                with p3:
                    preview_sort_by = st.selectbox("Sort table by", options=sort_options, index=0)
                with p4:
                    preview_top_n = st.number_input("Rows to display", min_value=10, max_value=1000, value=100, step=10)

                # v0.15.1: Consolidate state into result context
                context = build_deg_result_context(
                    workspace=workspace,
                    deg_input_obj=deg_input_obj,
                    comparison_column=comparison_column,
                    group_a=group_a,
                    group_b=group_b,
                    deg_res=st.session_state.deg_res,
                    p_thresh=p_thresh,
                    fc_thresh=fc_thresh,
                    sort_by=preview_sort_by,
                    top_n=int(preview_top_n)
                )

                st.info(
                    f"**比較条件**: `{context.comparison_column}` において **{context.group_a}** (A) vs **{context.group_b}** (B) の比較を行っています。\n\n"
                    f"💡 **解釈のヒント**: \n"
                    f"- `log2_fc` が **プラス(+)** ＝ **{context.group_a}** で高発現\n"
                    f"- `log2_fc` が **マイナス(-)** ＝ **{context.group_b}** で高発現\n"
                    f"- 有意判定は `padj < {context.threshold_snapshot.padj_threshold}` かつ `|log2_fc| > {context.threshold_snapshot.abs_log2_fc_threshold}` に基づきます。"
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Features Tested", context.summary_metrics.n_features_tested)
                c2.metric(f"Up in {context.group_a[:10]}...", context.summary_metrics.n_sig_up, help=f"Log2FC > {fc_thresh} & padj < {p_thresh}")
                c3.metric(f"Down in {context.group_a[:10]}...", context.summary_metrics.n_sig_down, help=f"Log2FC < -{fc_thresh} & padj < {p_thresh}")
                c4.metric("Max |log2FC|", f"{context.summary_metrics.max_abs_log2_fc:.3f}" if context.has_results else "NA")

                # Volcano Plot
                st.subheader("Volcano Plot")
                
                if context.summary_metrics.n_sig_up == 0 and context.summary_metrics.n_sig_down == 0:
                    st.warning("⚠️ 現在の閾値では有意遺伝子は 0 件です。閾値を緩めるか、p_value ベースでの確認もご検討ください。")
                
                volcano_df = context.result_table.copy()
                volcano_df["-log10(padj)"] = -np.log10(volcano_df["padj"].fillna(1.0).clip(lower=1e-300))
                
                def get_sig_category(row):
                    if row["padj"] < p_thresh and row["log2_fc"] > fc_thresh:
                        return f"Up in {context.group_a}"
                    elif row["padj"] < p_thresh and row["log2_fc"] < -fc_thresh:
                        return f"Down in {context.group_a}"
                    else:
                        return "Not Significant"

                volcano_df["Significance"] = volcano_df.apply(get_sig_category, axis=1)
                
                hover_cols = ["display_label", "gene_symbol", "feature_id", "log2_fc", "padj", "p_value"]
                hover_cols = [c for c in hover_cols if c in volcano_df.columns]

                fig = px.scatter(
                    volcano_df,
                    x="log2_fc",
                    y="-log10(padj)",
                    color="Significance",
                    color_discrete_map={
                        f"Up in {context.group_a}": "red",
                        f"Down in {context.group_a}": "blue",
                        "Not Significant": "lightgray"
                    },
                    hover_data=hover_cols,
                    title=f"Volcano Plot: {context.comparison_label}",
                    template="plotly_white"
                )
                
                fig.add_hline(y=-np.log10(p_thresh), line_dash="dash", line_color="black", annotation_text=f"padj = {p_thresh}")
                fig.add_vline(x=fc_thresh, line_dash="dash", line_color="black", annotation_text=f"log2FC = {fc_thresh}")
                fig.add_vline(x=-fc_thresh, line_dash="dash", line_color="black", annotation_text=f"log2FC = -{fc_thresh}")
                
                # Human-friendly Labeling
                top_up = volcano_df[volcano_df["Significance"] == f"Up in {context.group_a}"].sort_values("padj").head(10)
                top_down = volcano_df[volcano_df["Significance"] == f"Down in {context.group_a}"].sort_values("padj").head(10)
                label_candidates = pd.concat([top_up, top_down])
                
                for _, row in label_candidates.iterrows():
                    fig.add_annotation(
                        x=row["log2_fc"], y=row["-log10(padj)"],
                        text=row["display_label"], showarrow=True, arrowhead=1,
                        ax=40, ay=-40, bgcolor="rgba(255, 255, 255, 0.7)",
                        bordercolor="gray", borderwidth=1
                    )
                
                st.plotly_chart(fig, use_container_width=True)

                # Top up/down preview
                st.subheader("Top Differentially Expressed Genes")
                t1, t2 = st.columns(2)
                
                # Use context result table filtered for preview
                sig_up = context.result_table[(context.result_table["padj"] < p_thresh) & (context.result_table["log2_fc"] > fc_thresh)]
                sig_dn = context.result_table[(context.result_table["padj"] < p_thresh) & (context.result_table["log2_fc"] < -fc_thresh)]

                with t1:
                    st.write(f"**Top Up in {context.group_a}**")
                    display_cols_top = [c for c in ["display_label", "gene_symbol", "feature_id", "log2_fc", "padj"] if c in sig_up.columns]
                    st.dataframe(format_display_df(sig_up.sort_values("log2_fc", ascending=False).head(10)[display_cols_top]), use_container_width=True)
                with t2:
                    st.write(f"**Top Down in {context.group_a}**")
                    display_cols_top = [c for c in ["display_label", "gene_symbol", "feature_id", "log2_fc", "padj"] if c in sig_dn.columns]
                    st.dataframe(format_display_df(sig_dn.sort_values("log2_fc", ascending=True).head(10)[display_cols_top]), use_container_width=True)

                st.subheader("DEG Results Table")
                st.dataframe(format_display_df(context.result_table.head(int(preview_top_n))), use_container_width=True)
                
                # v0.15.2/3/4: Formal export payload, handoff contract and bundle
                export_payload = build_deg_export_payload(context, deg_input_obj)
                zip_filename = build_deg_export_bundle_filename(export_payload)
                # Pass explicit filename to bundle builder
                zip_bytes = build_deg_export_bundle(export_payload, bundle_filename=zip_filename)
                
                # Build handoff payload for UI preview
                handoff_payload = build_deg_handoff_payload(export_payload, zip_filename)

                # v0.16.1: Regsiter to portfolio
                record = build_comparison_record(context, export_payload, handoff_payload, zip_filename)
                st.session_state["comparison_portfolio_context"] = upsert_comparison_record(
                    st.session_state["comparison_portfolio_context"],
                    record
                )

                st.write("### エクスポート")
                portfolio_count = st.session_state["comparison_portfolio_context"].count
                st.success(f"✅ 解析結果をポートフォリオに登録しました (現在 {portfolio_count} 件蓄積)")
                st.info("解析結果、比較条件、実行メタデータをまとめた一式をダウンロードできます（推奨）。")
                
                e1, e2 = st.columns(2)
                with e1:
                    st.download_button(
                        label="📥 Download Report Bundle (ZIP)",
                        data=zip_bytes,
                        file_name=zip_filename,
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
                with e2:
                    csv_data = export_payload.result_table.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📄 Results Table only (CSV)",
                        data=csv_data,
                        file_name=f"deg_results_{context.group_a}_vs_{context.group_b}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with st.expander("Show Export / Handoff Payload Preview (JSON)", expanded=False):
                    tab1, tab2 = st.tabs(["Export Payload", "Handoff Contract"])
                    with tab1:
                        st.json(export_payload.summary.to_dict())
                        st.json(export_payload.metadata.to_dict())
                    with tab2:
                        st.json(handoff_payload.to_dict())

            except Exception as e:
                st.error(f"Failed to display DEG results: {e}")


def render_comparison_portfolio_section():
    """
    Render the Comparison Portfolio summary view (v0.16.2).
    Shows all comparisons registered in the current session.
    """
    st.header("15. Comparison Portfolio Summary")
    
    portfolio = st.session_state.get("comparison_portfolio_context")
    if not portfolio or portfolio.count == 0:
        st.info("💡 比較を実行するとポートフォリオに蓄積されます。まだ登録されている比較はありません。")
        return

    # 1. Summary Table
    st.subheader("蓄積された比較一覧")
    rows = build_comparison_portfolio_summary_rows(portfolio)
    df = build_comparison_portfolio_summary_dataframe(rows)
    
    # Format for display
    display_df = df.copy()
    if "max_abs_log2_fc" in display_df.columns:
        display_df["max_abs_log2_fc"] = display_df["max_abs_log2_fc"].map(lambda x: f"{x:.4f}" if x is not None else "NA")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # 2. Minimal Preview
    st.subheader("比較詳細プレビュー")
    selected_id = st.selectbox(
        "プレビューする比較を選択",
        options=portfolio.comparison_ids,
        index=portfolio.count - 1  # Default to latest
    )
    
    record = get_comparison_record(portfolio, selected_id)
    if record:
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Label:** `{record.comparison_label}`")
            st.write(f"**Matrix:** `{record.export_payload.metadata.matrix_kind}`")
            st.write(f"**ID:** `{record.comparison_id}`")
        with c2:
            metrics = record.summary_metrics
            st.write(f"**Sig. Up:** `{metrics.n_sig_up}`")
            st.write(f"**Sig. Dn:** `{metrics.n_sig_down}`")
            st.write(f"**Bundle:** `{record.bundle_filename}`")
        
        with st.expander("Show Detailed Metrics & Metadata", expanded=False):
            st.json(record.handoff_payload.to_dict())

    # 3. Portfolio Export Bundle (v0.16.3)
    st.subheader("ポートフォリオのエクスポート")
    st.info("蓄積された全ての比較結果を一つの成果物（Portfolio Bundle）としてエクスポートできます。")
    
    portfolio_zip_filename = build_comparison_portfolio_bundle_filename(portfolio)
    
    try:
        # Build payload once for reuse in ZIP and Handoff
        export_payload = build_comparison_portfolio_export_payload(portfolio)
        portfolio_zip_bytes = build_comparison_portfolio_export_bundle(portfolio)
        
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label="Download Portfolio Bundle (ZIP)",
                data=portfolio_zip_bytes,
                file_name=portfolio_zip_filename,
                mime="application/zip",
                key="download_portfolio_bundle"
            )
        with c2:
            st.write(f"**Bundle Filename:** `{portfolio_zip_filename}`")
            st.caption("Contents: manifest.json, index.json, handoff_contract.json, comparisons/")
            
        with st.expander("Explore Bundle Structure Preview", expanded=False):
            st.code(f"""
{portfolio_zip_filename}
├── portfolio_manifest.json
├── comparison_index.json
├── portfolio_handoff_contract.json
└── comparisons/
    {"".join([f"├── {cid}/" for cid in portfolio.comparison_ids[:3]])}
    { "..." if portfolio.count > 3 else ""}
            """, language="text")

        # 4. Handoff Contract Preview (v0.16.4)
        st.subheader("Handoff Contract Preview")
        st.info("下流ツールがこのポートフォリオを認識するための正式な定義（Contract）です。")
        
        handoff_contract = build_comparison_portfolio_handoff_payload(
            portfolio, export_payload, portfolio_zip_filename
        )
        
        h1, h2 = st.columns(2)
        with h1:
            st.write(f"**Portfolio ID:** `{handoff_contract.portfolio_id}`")
            st.write(f"**Matrix Kinds:** `{', '.join(handoff_contract.matrix_kinds)}`")
        with h2:
            sys_sum = handoff_contract.feature_id_system_summary
            st.write(f"**ID Systems:** `{', '.join(sys_sum.feature_id_systems)}` ({'⚠️ Mixed' if sys_sum.is_mixed else 'Consistent'})")
            st.write(f"**Total Comparisons:** `{len(handoff_contract.included_comparison_ids)}`")

        with st.expander("Show Portfolio Handoff JSON", expanded=False):
            st.json(handoff_contract.to_dict())

    except Exception as e:
        st.error(f"Failed to prepare portfolio export: {e}")
    else:
        st.info("Build a valid comparison design to run DEG analysis.")

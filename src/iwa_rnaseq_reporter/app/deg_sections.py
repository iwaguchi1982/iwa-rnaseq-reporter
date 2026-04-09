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

                deg_res = st.session_state.deg_res
                res_df = deg_res.result_table.copy()

                # Optimized: Use the new standardized annotation join
                res_df = add_display_labels(res_df, workspace.dataset.feature_annotation)

                if preview_sort_by in res_df.columns:
                    ascending = True if preview_sort_by in ["padj", "p_value"] else False
                    res_df = res_df.sort_values(by=preview_sort_by, ascending=ascending)

                preferred_cols = [
                    "rank_by_padj", "display_label", "gene_symbol", "feature_id", "log2_fc", 
                    "padj", "p_value", "direction", "mean_group_a", "mean_group_b", "abs_log2_fc"
                ]
                display_cols = [c for c in preferred_cols if c in res_df.columns]
                other_cols = [c for c in res_df.columns if c not in display_cols]
                res_df = res_df[display_cols + other_cols]

                sig_up = res_df[(res_df["padj"] < p_thresh) & (res_df["log2_fc"] > fc_thresh)]
                sig_dn = res_df[(res_df["padj"] < p_thresh) & (res_df["log2_fc"] < -fc_thresh)]

                st.info(
                    f"**比較条件**: `{comparison_column}` において **{deg_res.group_a}** (A) vs **{deg_res.group_b}** (B) の比較を行っています。\n\n"
                    f"💡 **解釈のヒント**: \n"
                    f"- `log2_fc` が **プラス(+)** ＝ **{deg_res.group_a}** で高発現\n"
                    f"- `log2_fc` が **マイナス(-)** ＝ **{deg_res.group_b}** で高発現\n"
                    f"- 有意判定は `padj < {p_thresh}` かつ `|log2_fc| > {fc_thresh}` に基づきます。"
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Features Tested", deg_res.n_features_tested)
                c2.metric(f"Up in {deg_res.group_a[:10]}...", len(sig_up), help=f"Log2FC > {fc_thresh} & padj < {p_thresh}")
                c3.metric(f"Down in {deg_res.group_a[:10]}...", len(sig_dn), help=f"Log2FC < -{fc_thresh} & padj < {p_thresh}")
                c4.metric("Max |log2FC|", f"{res_df['abs_log2_fc'].max():.3f}" if not res_df.empty else "NA")

                # Volcano Plot
                st.subheader("Volcano Plot")
                
                if len(sig_up) == 0 and len(sig_dn) == 0:
                    st.warning("⚠️ 現在の閾値では有意遺伝子は 0 件です。閾値を緩めるか、p_value ベースでの確認もご検討ください。")
                
                volcano_df = res_df.copy()
                volcano_df["-log10(padj)"] = -np.log10(volcano_df["padj"].fillna(1.0).clip(lower=1e-300))
                
                def get_sig_category(row):
                    if row["padj"] < p_thresh and row["log2_fc"] > fc_thresh:
                        return f"Up in {deg_res.group_a}"
                    elif row["padj"] < p_thresh and row["log2_fc"] < -fc_thresh:
                        return f"Down in {deg_res.group_a}"
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
                        f"Up in {deg_res.group_a}": "red",
                        f"Down in {deg_res.group_a}": "blue",
                        "Not Significant": "lightgray"
                    },
                    hover_data=hover_cols,
                    title=f"Volcano Plot: {deg_res.group_a} vs {deg_res.group_b}",
                    template="plotly_white"
                )
                
                fig.add_hline(y=-np.log10(p_thresh), line_dash="dash", line_color="black", annotation_text=f"padj = {p_thresh}")
                fig.add_vline(x=fc_thresh, line_dash="dash", line_color="black", annotation_text=f"log2FC = {fc_thresh}")
                fig.add_vline(x=-fc_thresh, line_dash="dash", line_color="black", annotation_text=f"log2FC = -{fc_thresh}")
                
                # Human-friendly Labeling
                top_up = volcano_df[volcano_df["Significance"] == f"Up in {deg_res.group_a}"].sort_values("padj").head(10)
                top_down = volcano_df[volcano_df["Significance"] == f"Down in {deg_res.group_a}"].sort_values("padj").head(10)
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
                with t1:
                    st.write(f"**Top Up in {deg_res.group_a}**")
                    display_cols_top = [c for c in ["display_label", "gene_symbol", "feature_id", "log2_fc", "padj"] if c in sig_up.columns]
                    st.dataframe(format_display_df(sig_up.sort_values("log2_fc", ascending=False).head(10)[display_cols_top]), use_container_width=True)
                with t2:
                    st.write(f"**Top Down in {deg_res.group_a}**")
                    display_cols_top = [c for c in ["display_label", "gene_symbol", "feature_id", "log2_fc", "padj"] if c in sig_dn.columns]
                    st.dataframe(format_display_df(sig_dn.sort_values("log2_fc", ascending=True).head(10)[display_cols_top]), use_container_width=True)

                st.subheader("DEG Results Table")
                st.dataframe(format_display_df(res_df.head(int(preview_top_n))), use_container_width=True)
                
                st.write("### エクスポート")
                st.caption("現在ブラウザ上でプレビューされている全てのDEG結果（全件）をCSV形式で保存します。")
                csv = res_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 フルDEG結果をCSVでダウンロード",
                    data=csv,
                    file_name=f"deg_results_{deg_res.group_a}_vs_{deg_res.group_b}.csv",
                    mime="text/csv",
                    type="primary",
                )

            except Exception as e:
                st.error(f"Failed to display DEG results: {e}")
    else:
        st.info("Build a valid comparison design to run DEG analysis.")

"""Generates Report.docx with KIU thesis formatting."""

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DOCX_PATH = r"C:\Users\ASUS_ZEPHYRUS\Desktop\GraphGuard\Report.docx"

doc = Document()

# ── Page layout ──────────────────────────────────────────────────────────────
section = doc.sections[0]
section.left_margin   = Cm(3.0)
section.right_margin  = Cm(1.5)
section.top_margin    = Cm(2.5)
section.bottom_margin = Cm(2.5)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(para, size=12, bold=False, italic=False,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        space_before=0, space_after=0,
        line_spacing=1.5, keep_with_next=False):
    pf = para.paragraph_format
    pf.alignment         = align
    pf.space_before      = Pt(space_before)
    pf.space_after       = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing      = line_spacing
    pf.keep_with_next    = keep_with_next
    for run in para.runs:
        run.font.name   = "Times New Roman"
        run.font.size   = Pt(size)
        run.font.bold   = bold
        run.font.italic = italic
    return para

def add_para(text, size=12, bold=False, italic=False,
             align=WD_ALIGN_PARAGRAPH.LEFT,
             space_before=0, space_after=6, line_spacing=1.5,
             keep_with_next=False):
    p   = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name   = "Times New Roman"
    run.font.size   = Pt(size)
    run.font.bold   = bold
    run.font.italic = italic
    fmt(p, size=size, bold=bold, italic=italic, align=align,
        space_before=space_before, space_after=space_after,
        line_spacing=line_spacing, keep_with_next=keep_with_next)
    return p

def add_heading(text, level=1):
    if level == 1:
        return add_para(text, size=14, bold=True,
                        align=WD_ALIGN_PARAGRAPH.CENTER,
                        space_before=12, space_after=12,
                        line_spacing=1.5, keep_with_next=True)
    elif level == 2:
        return add_para(text, size=12, bold=True,
                        space_before=12, space_after=6,
                        line_spacing=1.5, keep_with_next=True)
    else:
        return add_para(text, size=12, bold=True, italic=True,
                        space_before=6, space_after=3,
                        line_spacing=1.5, keep_with_next=True)

def add_body(text, first_indent=True):
    p = add_para(text, size=12, space_before=0, space_after=6, line_spacing=1.5)
    if first_indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    return p

def page_break():
    doc.add_page_break()

def add_blank():
    add_para("", space_after=0)

def add_toc_line(title, page, bold=False):
    """One line in the table of contents with dot leader."""
    if not title:
        add_para("", size=12, space_before=0, space_after=2)
        return
    p  = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before      = Pt(0)
    pf.space_after       = Pt(2)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing      = 1.15
    tabs = OxmlElement("w:tabs")
    tab  = OxmlElement("w:tab")
    tab.set(qn("w:val"),    "right")
    tab.set(qn("w:leader"), "dot")
    tab.set(qn("w:pos"),    str(int(16.5 * 1440 / 2.54)))  # twips
    tabs.append(tab)
    if p._p.pPr is not None:
        p._p.pPr.append(tabs)
    run = p.add_run(title + "\t" + page)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = bold

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 - TITLE PAGE
# ─────────────────────────────────────────────────────────────────────────────
for _ in range(4):
    add_blank()

add_para("KUTAISI INTERNATIONAL UNIVERSITY", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
add_para("School of Computer Science", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
add_para("Bachelor of Science in Computer Science", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

add_para("Soso Pkhakadze", size=13, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
add_para("Guga Mepisashvili", size=13, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
add_para("Davit Karseladze", size=13, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

add_para(
    "CALL GRAPH-AUGMENTED IMPACT ANALYSIS FOR C PROGRAMS "
    "USING LARGE LANGUAGE MODELS",
    size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36
)

add_para("Bachelor's Thesis", size=12, italic=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

add_para("Supervisor: Professor Walter Tichy", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
add_para("Co-supervisor: Shota Elkanishvili", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)

for _ in range(4):
    add_blank()

add_para("Kutaisi, 2025", size=12, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)

page_break()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 - DECLARATION
# ─────────────────────────────────────────────────────────────────────────────
add_heading("Declaration", level=1)

add_body(
    "We declare that this thesis is our own original work, carried out under the "
    "supervision of Professor Walter Tichy and co-supervisor Shota Elkanishvili. "
    "All sources we consulted and quoted are properly cited. This thesis has not "
    "been submitted for assessment at any other institution.",
    first_indent=False
)

add_blank()
add_para("Students:", size=12, bold=True, space_after=6)

for name in ["Soso Pkhakadze", "Guga Mepisashvili", "Davit Karseladze"]:
    add_para(name, size=12, space_after=2)
    add_para("Signature: ___________________________", size=12, space_after=2)
    add_para("Date: May 2025", size=12, space_after=10)

add_blank()
add_para("Supervisor Confirmation:", size=12, bold=True, space_after=6)
add_body(
    "I confirm that this thesis was completed under my supervision and meets the "
    "formal requirements for submission.",
    first_indent=False
)
add_blank()
add_para("Professor Walter Tichy", size=12, space_after=2)
add_para("Signature: ___________________________", size=12, space_after=2)
add_para("Date: May 2025", size=12, space_after=0)

page_break()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 - ABSTRACT
# ─────────────────────────────────────────────────────────────────────────────
add_heading("Abstract", level=1)

add_body(
    "When a developer modifies code in a large C project, figuring out which other "
    "functions or modules are affected is rarely straightforward. This thesis presents "
    "GraphGuard, a tool that addresses this problem by combining static call graph "
    "analysis with large language model (LLM) reasoning.",
    first_indent=False
)

add_body(
    "The core idea is simple: an LLM asked to predict the impact of a change needs "
    "to know what calls what. Without that information, the model can only guess based "
    "on naming conventions and surface patterns. GraphGuard constructs a call graph "
    "from the project source using libclang, identifies the set of changed functions "
    "from a git diff, and provides the LLM with structured call relationship context "
    "alongside the diff."
)

add_body(
    "We compare three approaches. The Baseline Approach provides only the diff to the "
    "LLM with no call graph context. The Context-Augmented Approach provides the diff "
    "together with a summary of direct callers, callees, and transitive call chains "
    "from the changed functions. The Agent-Based Approach gives the LLM access to a "
    "set of callable tools and lets it query the call graph interactively, requesting "
    "the information it needs as it reasons through the problem."
)

add_body(
    "Evaluation across 50 open-source C projects shows substantial differences. The "
    "Baseline Approach achieves an average F1 score of 0.52, while the "
    "Context-Augmented Approach achieves 0.98 on the same dataset. These results "
    "suggest that structural context - knowing the actual call relationships in the "
    "specific project - is the main factor determining accuracy, not LLM capability alone."
)

add_blank()
p    = doc.add_paragraph()
run1 = p.add_run("Keywords: ")
run1.font.name = "Times New Roman"
run1.font.size = Pt(12)
run1.font.bold = True
run2 = p.add_run(
    "code change impact analysis, call graph, large language models, "
    "static analysis, C programming, LLM agents, libclang"
)
run2.font.name = "Times New Roman"
run2.font.size = Pt(12)
fmt(p, space_before=6, space_after=0)

page_break()

# ─────────────────────────────────────────────────────────────────────────────
# PAGES 4-5 - TABLE OF CONTENTS
# ─────────────────────────────────────────────────────────────────────────────
add_heading("Table of Contents", level=1)

toc = [
    ("Declaration",                                          "2",  False),
    ("Abstract",                                             "3",  False),
    ("Table of Contents",                                    "4",  False),
    ("List of Figures",                                      "6",  False),
    ("",                                                     "",   False),
    ("Chapter 1: Introduction",                              "7",  True),
    ("    1.1  Problem Statement",                           "7",  False),
    ("    1.2  Research Objectives",                         "8",  False),
    ("    1.3  Hypothesis",                                  "9",  False),
    ("    1.4  Methodology Overview",                        "9",  False),
    ("    1.5  Thesis Structure",                            "10", False),
    ("",                                                     "",   False),
    ("Chapter 2: Literature Review",                         "11", True),
    ("    2.1  Code Change Impact Analysis",                 "11", False),
    ("    2.2  Static Analysis and Call Graphs for C",       "12", False),
    ("    2.3  Large Language Models for Code",              "13", False),
    ("    2.4  Tool Use and Agent-Based Reasoning",          "14", False),
    ("    2.5  Research Gap",                                "15", False),
    ("",                                                     "",   False),
    ("Chapter 3: System Design and Implementation",          "16", True),
    ("    3.1  Architecture Overview",                       "16", False),
    ("    3.2  Call Graph Construction",                     "17", False),
    ("    3.3  Baseline Approach",                           "18", False),
    ("    3.4  Context-Augmented Approach",                  "19", False),
    ("    3.5  Agent-Based Approach",                        "20", False),
    ("    3.6  Caching and Incremental Updates",             "21", False),
    ("    3.7  VS Code Extension",                           "22", False),
    ("",                                                     "",   False),
    ("Chapter 4: Experimental Setup",                        "23", True),
    ("    4.1  Dataset",                                     "23", False),
    ("    4.2  Ground Truth Construction",                   "24", False),
    ("    4.3  Evaluation Metrics",                          "25", False),
    ("    4.4  Models and API Configuration",                "25", False),
    ("",                                                     "",   False),
    ("Chapter 5: Results and Analysis",                      "26", True),
    ("    5.1  Quantitative Results",                        "26", False),
    ("    5.2  Error Analysis",                              "28", False),
    ("    5.3  Discussion",                                  "30", False),
    ("",                                                     "",   False),
    ("Chapter 6: Conclusion",                                "32", True),
    ("    6.1  Summary of Contributions",                    "32", False),
    ("    6.2  Limitations",                                 "33", False),
    ("    6.3  Future Work",                                 "34", False),
    ("",                                                     "",   False),
    ("References",                                           "36", True),
]

for title, page, bold in toc:
    add_toc_line(title, page, bold)

page_break()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6 - LIST OF FIGURES
# ─────────────────────────────────────────────────────────────────────────────
add_heading("List of Figures", level=1)

figures = [
    ("Figure 3.1", "Overall architecture of GraphGuard",                   "17"),
    ("Figure 3.2", "Example call graph for the demo banking project",       "18"),
    ("Figure 3.3", "Baseline Approach prompt structure",                    "19"),
    ("Figure 3.4", "Context-Augmented Approach prompt structure",           "20"),
    ("Figure 3.5", "Agent-Based Approach sequence diagram",                 "21"),
    ("Figure 4.1", "Distribution of project sizes in the dataset",         "24"),
    ("Figure 5.1", "F1 scores per project for all three approaches",        "27"),
    ("Figure 5.2", "Precision-recall curves: Baseline vs Context-Augmented","28"),
    ("Figure 5.3", "Token usage breakdown by approach",                     "29"),
]

for label, caption, page in figures:
    p   = doc.add_paragraph()
    pf  = p.paragraph_format
    pf.space_before      = Pt(0)
    pf.space_after       = Pt(4)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing      = 1.15
    run = p.add_run(f"{label} - {caption}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)

page_break()

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 1 - INTRODUCTION
# ─────────────────────────────────────────────────────────────────────────────
add_heading("CHAPTER 1: INTRODUCTION", level=1)

add_heading("1.1  Problem Statement", level=2)

add_body(
    "When a developer changes a function in a C codebase, a natural question follows: "
    "what else might break? In a small project with a few hundred lines of code, a "
    "developer can usually answer this from memory. In a project with tens of thousands "
    "of lines spread across many files, the question becomes genuinely difficult. A "
    "change to a low-level utility function can cascade through many layers of the "
    "call hierarchy and affect modules the developer never thought to check."
)

add_body(
    "This problem - determining which parts of a software system are affected by a "
    "code change - is called code change impact analysis (CIA). It has practical "
    "consequences: developers who miss affected functions during code review may "
    "introduce regressions that only surface after merging or during production "
    "incidents. Thorough impact analysis requires either deep familiarity with the "
    "codebase or dedicated tooling to trace call relationships and dependencies "
    "systematically."
)

add_body(
    "Traditional static analysis tools do exist for this purpose. Tools like GNU cflow "
    "and Understand can build call graphs and trace dependencies in C programs. However, "
    "they have seen limited adoption outside of safety-critical and embedded development "
    "contexts. The main barriers are setup complexity, the need to integrate them into a "
    "build system, and the learning curve for interpreting results. Many developers "
    "working on open-source C projects do not use any CIA tool at all."
)

add_body(
    "Large language models have changed expectations around what developers can ask a "
    "computer to help with. A developer can describe a bug in natural language and get "
    "a plausible explanation, paste a function and ask what it does, or request a "
    "review of a small diff. A natural extension is to paste a diff and ask: what else "
    "in this codebase will this change affect? This approach requires no special "
    "tooling and fits into a developer's existing workflow without any setup."
)

add_body(
    "The problem is that an LLM given only a diff cannot know what calls what in a "
    "specific project. It can recognize patterns - a function named handle_error "
    "probably affects error handling paths, a function that modifies a shared struct "
    "probably affects code that reads that struct - but it cannot trace the actual "
    "call graph of the project. Two projects might have completely different call "
    "structures for functions with identical names. Without seeing those relationships, "
    "the model's predictions are closer to informed guesses than structural reasoning."
)

add_body(
    "This thesis investigates what happens when an LLM is given that structural "
    "information. The hypothesis is that providing call graph context - specifically, "
    "which functions call the changed function, and which functions those callers call - "
    "will substantially improve prediction quality. We build a tool called GraphGuard "
    "that automates this process and evaluate it across 50 open-source C projects."
)

add_heading("1.2  Research Objectives", level=2)

add_body(
    "This thesis pursues three main objectives. The first is to build a tool that is "
    "practical and usable - not a research prototype that requires specialized expertise "
    "to operate, but something a developer can run from a terminal or use through an IDE "
    "plugin. This means handling real-world complications: projects that use non-standard "
    "LLVM installations, codebases with multiple source directories, and the requirement "
    "to rebuild the call graph only when files actually change."
)

add_body(
    "The second objective is to quantify the difference between providing only the diff "
    "versus providing call graph context alongside the diff. We do this with a controlled "
    "comparison across 50 projects, using the same LLM model for both approaches and the "
    "same evaluation protocol. Precision, recall, and F1 score over the set of affected "
    "functions serve as the primary metrics."
)

add_body(
    "The third objective is to explore agent-based analysis as an alternative to static "
    "context provision. In this approach, the LLM is given a set of callable tools - "
    "find callers, find callees, read function source, search for patterns - and queries "
    "the call graph interactively as it reasons. This mirrors how a developer would "
    "investigate the issue manually, and it may handle cases where the relevant context "
    "is too large to include upfront in a single prompt."
)

add_heading("1.3  Hypothesis", level=2)

add_body(
    "The main hypothesis is that providing call graph context to an LLM substantially "
    "improves its accuracy on code change impact analysis compared to providing only the "
    "diff. Specifically, we expect both precision and recall to improve, because the LLM "
    "will have access to the actual call relationships in the project rather than relying "
    "on naming patterns and general programming knowledge."
)

add_body(
    "A secondary hypothesis is that the Agent-Based Approach performs at least as well "
    "as the Context-Augmented Approach on the test set, and will perform better on "
    "larger projects where the full call graph context cannot fit in a single prompt."
)

add_heading("1.4  Methodology Overview", level=2)

add_body(
    "GraphGuard is implemented in Python. It parses C source files using libclang, the "
    "C-family frontend of the LLVM compiler infrastructure, to extract function "
    "definitions and call relationships. From these, it constructs a directed call graph "
    "where each node is a function and each edge represents a direct call. The graph is "
    "serialized to disk and loaded on subsequent runs, with file modification time checks "
    "to trigger rebuilds only when source files have changed."
)

add_body(
    "To identify changed functions for a given analysis run, GraphGuard calls git diff "
    "on the working tree, parses the unified diff output to locate which function bodies "
    "were modified, and then uses the call graph to find all functions reachable from "
    "those modified functions through caller relationships."
)

add_body(
    "For evaluation, we built a dataset of 50 open-source C projects ranging from small "
    "single-file utilities to medium-sized codebases with around 15,000 lines of code. "
    "For each project, we identified representative commits that modified between one and "
    "five functions - typical of a focused change. We used the call graph computed from "
    "the parent commit to derive ground truth: the set of all functions that transitively "
    "call any of the modified functions. All three approaches receive the same diff and "
    "are asked to predict the same set of affected functions."
)

add_heading("1.5  Thesis Structure", level=2)

add_body(
    "Chapter 2 reviews related work on code change impact analysis, static call graph "
    "construction for C, large language models applied to code tasks, and agent-based "
    "approaches to tool use. Chapter 3 describes the design and implementation of "
    "GraphGuard, covering all three analysis approaches and the VS Code extension. "
    "Chapter 4 describes the experimental setup in detail. Chapter 5 presents results "
    "and analysis. Chapter 6 concludes with a summary of contributions, a discussion "
    "of limitations, and directions for future work."
)

page_break()

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 2 - LITERATURE REVIEW
# ─────────────────────────────────────────────────────────────────────────────
add_heading("CHAPTER 2: LITERATURE REVIEW", level=1)

add_heading("2.1  Code Change Impact Analysis", level=2)

add_body(
    "The problem of determining what a code change affects has been studied in software "
    "engineering since at least the early 1990s. Lehnert (2011) provides a comprehensive "
    "survey of the field. His taxonomy distinguishes between static approaches, which "
    "analyze code structure without executing it, and dynamic approaches, which trace "
    "execution paths through instrumentation or test runs. Static approaches are faster "
    "and require no working test suite, but they may flag call paths that are never "
    "exercised at runtime. Dynamic approaches are more precise but depend on the "
    "quality of available test coverage."
)

add_body(
    "Early static CIA tools were rooted in structured design methods. Bohner and Arnold "
    "(1996) surveyed industry practice and found that most change impact work was done "
    "manually, with developers relying on code knowledge and documentation. They argued "
    "for more systematic dependency analysis and proposed a taxonomy of software "
    "relationships relevant to CIA. Their framework distinguished syntactic dependencies - "
    "direct function calls, variable references - from semantic dependencies, which are "
    "harder to capture automatically."
)

add_body(
    "For source-code-level analysis, the dominant approach has been to build a dependency "
    "graph where nodes are software entities such as functions, modules, or variables, "
    "and edges represent depends-on relationships. The analysis then computes the "
    "transitive closure of that graph starting from the changed entities. Functions "
    "reachable from the changed code through dependency edges are flagged as potentially "
    "affected. Arnold and Bohner (1993) investigated dependency types and how to extract "
    "them from C source code. Reps, Horwitz, and Sagiv (1995) developed program slicing "
    "algorithms closely related to CIA - a backward slice of a program point captures "
    "all statements that could affect the value at that point, which is analogous to "
    "finding all callers in the impact analysis sense."
)

add_body(
    "The challenge in applying these methods to C specifically is the presence of "
    "function pointers. Unlike Java or C++, C has no method dispatch mechanism that "
    "can always be resolved statically - any function pointer could in principle point "
    "to any compatible function. Static call graphs for C programs are therefore "
    "inherently approximate. Practical tools either ignore function pointer targets, "
    "potentially missing impact paths, or include all reachable functions as possible "
    "targets, potentially over-approximating the impact set."
)

add_heading("2.2  Static Analysis and Call Graphs for C", level=2)

add_body(
    "LibClang is the C and C++ frontend of the LLVM compiler infrastructure, exposed "
    "as a stable C API with Python bindings through the clang package. Unlike parsing "
    "with regular expressions or simple text processing, libclang produces a full "
    "abstract syntax tree (AST) that respects preprocessor macros, handles complex "
    "type expressions, and correctly processes all legal C syntax. For the purpose "
    "of extracting function definitions and call sites, the Python bindings provide "
    "a straightforward tree traversal interface."
)

add_body(
    "Several tools have offered call graph generation for C as a built-in feature. "
    "GNU cflow (Meyering, 1997) generates call graphs from C source files and has been "
    "part of the GNU project for decades. It is simple to use but does not handle some "
    "modern C constructs well. Doxygen (van Heesch, 1997), primarily a documentation "
    "generator, includes optional call graph output using Graphviz, but requires "
    "significant configuration and is aimed at visual diagrams rather than programmatic "
    "analysis. Understand from Scientific Toolworks is a commercial tool with more "
    "complete call graph support, but its cost puts it out of reach for many projects."
)

add_body(
    "More recent work has used Joern (Yamaguchi et al., 2014), a code analysis platform "
    "that builds a code property graph combining the AST, control flow graph, and program "
    "dependency graph. Joern supports C and C++ and has been widely used in security "
    "research for vulnerability analysis. Its call graph capabilities are more complete "
    "than libclang-based approaches because it handles more edge cases, but it requires "
    "a separate installation and has a steeper learning curve. GraphGuard's call graph "
    "module is simpler than any of these: it handles direct function calls correctly, "
    "skips indirect calls through function pointers, and is designed to be fast enough "
    "that rebuilding for a medium-sized project takes only a few seconds."
)

add_heading("2.3  Large Language Models for Code", level=2)

add_body(
    "The publication of Codex (Chen et al., 2021) marked the beginning of serious "
    "interest in applying large language models to programming tasks. Codex was a "
    "GPT-3 variant fine-tuned on public code from GitHub, and it demonstrated that a "
    "language model could generate functionally correct code from natural language "
    "descriptions at a level that passed automated test suites. The HumanEval benchmark "
    "introduced in that paper has since become a standard evaluation for code generation."
)

add_body(
    "Since Codex, code capability has become a standard feature of frontier language "
    "models. GPT-4 (OpenAI, 2023), Claude (Anthropic, 2023), and Gemini (Google, 2024) "
    "all show strong performance on code benchmarks, and specialized code models like "
    "DeepSeek-Coder (Guo et al., 2024) and CodeLlama (Roziere et al., 2023) push "
    "performance further by training specifically on code data. These models can explain "
    "code, identify bugs, suggest refactors, and complete partial implementations. "
    "Beyond code generation, LLMs have been applied to bug detection (Prenner & Robbes, "
    "2021), test generation (Schafer et al., 2023), and automated code review "
    "(Tufano et al., 2021)."
)

add_body(
    "For impact analysis specifically, the literature is sparse. White et al. (2023) "
    "surveyed applications of ChatGPT to software engineering and mentioned impact "
    "analysis informally, noting that the model could identify obvious impact paths "
    "but struggled with project-specific relationships not apparent from naming or "
    "conventions alone. Ni et al. (2023) studied LLM performance on various code "
    "understanding tasks and found that models often relied on surface-level patterns "
    "rather than structural reasoning. Both findings are consistent with the expectation "
    "that structured program analysis context should improve accuracy."
)

add_heading("2.4  Tool Use and Agent-Based Reasoning", level=2)

add_body(
    "The ability to call external tools during generation has substantially expanded "
    "what language models can accomplish. Schick et al. (2023) introduced Toolformer, "
    "a model that learned to insert API calls into its own generated text through "
    "fine-tuning on self-generated examples. More recently, OpenAI's function calling "
    "feature and Anthropic's tool use API provide a standard mechanism: the model is "
    "given a set of tool schemas in JSON format, requests tool calls in its response, "
    "an external system executes those calls, and the results are fed back to continue "
    "generation. This loop repeats until the model produces a final answer."
)

add_body(
    "The ReAct framework (Yao et al., 2022) demonstrated that interleaving reasoning "
    "and action - generating a thought, then an action, then observing the result, "
    "then reasoning again - outperforms either pure chain-of-thought reasoning or "
    "pure action sequences on tasks that require retrieving information from external "
    "sources. ReAct has influenced many subsequent agent frameworks and provides the "
    "conceptual basis for the Agent-Based Approach implemented in this thesis."
)

add_body(
    "For code tasks, agent-based approaches have shown strong results on complex "
    "multi-step problems. SWE-agent (Yang et al., 2024) applies a language model "
    "agent to GitHub issues, letting it edit files, run tests, and navigate codebases "
    "to produce patches. It achieves competitive results on the SWE-bench benchmark, "
    "which requires fixing real GitHub issues in open-source Python projects. Devin "
    "(Cognition, 2024) takes a similar approach with a broader set of developer "
    "actions including browser navigation and terminal use. Both systems illustrate "
    "that interactive exploration - rather than reasoning from a fixed context window - "
    "is often more effective for tasks that require understanding a specific codebase."
)

add_heading("2.5  Research Gap", level=2)

add_body(
    "The work reviewed in this chapter falls into two separate streams. On one side, "
    "code change impact analysis has decades of theoretical and tool development behind "
    "it, but has not been connected to modern LLM capabilities. On the other side, "
    "LLMs for code are well-studied for generation and summarization tasks, but rarely "
    "evaluated on impact analysis, and when they are, they receive only the changed "
    "code rather than any structural program context."
)

add_body(
    "This thesis connects these two streams. We evaluate, specifically for C projects, "
    "whether providing call graph context to an LLM improves impact analysis accuracy "
    "over a baseline that receives only the diff. We also compare static context "
    "provision against an interactive agent approach where the LLM queries the call "
    "graph as it reasons. To our knowledge, this specific combination has not been "
    "studied in prior published work, and the C language presents particular challenges "
    "due to its lack of a module system and its use of function pointers."
)

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
doc.save(DOCX_PATH)
print(f"Saved: {DOCX_PATH}")

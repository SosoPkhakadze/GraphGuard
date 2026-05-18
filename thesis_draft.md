# Formatting Note (remove before final submission)
# Times New Roman 12pt, 1.5 line spacing
# Margins: Left 3cm, Right 1.5cm, Top 2.5cm, Bottom 2.5cm
# APA citation style
# Target: 30-50 pages total. This draft covers first 14 pages.

---

<!-- PAGE 1: TITLE PAGE -->

&nbsp;

&nbsp;

&nbsp;

**KUTAISI INTERNATIONAL UNIVERSITY**

School of Computer Science and Engineering

Bachelor of Science in Computer Science

&nbsp;

&nbsp;

**Soso Pkhakadze**

&nbsp;

&nbsp;

# CALL GRAPH-AUGMENTED IMPACT ANALYSIS FOR C PROGRAMS USING LARGE LANGUAGE MODELS

&nbsp;

&nbsp;

Bachelor's Thesis

&nbsp;

Supervisor: Shota [Surname]

[Academic Title, School of Computer Science and Engineering]

&nbsp;

&nbsp;

&nbsp;

Kutaisi, 2025

---

<!-- PAGE 2: DECLARATION -->

## Declaration

I declare that this thesis is my own original work and was completed under the supervision of [Supervisor Name]. All sources I consulted and quoted are properly cited. This thesis has not been submitted for assessment at any other institution.

&nbsp;

Student: Soso Pkhakadze

Signature: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Date: May 2025

&nbsp;

&nbsp;

Supervisor Confirmation:

I confirm that this thesis was completed under my supervision and that it meets the formal requirements for submission.

&nbsp;

Supervisor: [Name Surname]

Signature: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Date: May 2025

---

<!-- PAGE 3: ABSTRACT -->

## Abstract

When a developer modifies code in a large C project, figuring out which other functions or modules are affected is rarely straightforward. This thesis presents GraphGuard, a tool that addresses this problem by combining static call graph analysis with large language model (LLM) reasoning.

The core idea is simple: an LLM asked to predict the impact of a change needs to know what calls what. Without that information, the model can only guess based on naming conventions and surface patterns. GraphGuard constructs a call graph from the project source using libclang, identifies the set of changed functions from a git diff, and provides the LLM with structured call relationship context alongside the diff.

We compare three approaches. The first (Friend 1) provides only the diff to the LLM - no call graph context. The second (Friend 2) provides the diff together with a summary of direct callers, callees, and transitive call chains from the changed functions. The third (Friend 3) gives the LLM access to a set of tools and lets it query the call graph interactively, requesting the information it needs as it reasons.

Evaluation across 50 open-source C projects shows substantial differences. Friend 1 achieves an average F1 score of 0.52, while Friend 2 achieves 0.98 on the same dataset. These results suggest that structural context - knowing the actual call relationships in the specific project - is the main factor determining accuracy, not LLM capability alone.

**Keywords:** code change impact analysis, call graph, large language models, static analysis, C, LLM agents, libclang

---

<!-- PAGES 4-5: TABLE OF CONTENTS -->

## Table of Contents

Declaration ..............................................................2

Abstract .................................................................3

Table of Contents ........................................................4

List of Figures ..........................................................6

**Chapter 1: Introduction** ...............................................7

&nbsp;&nbsp;&nbsp;&nbsp;1.1 Problem Statement ...............................................7

&nbsp;&nbsp;&nbsp;&nbsp;1.2 Research Objectives .............................................8

&nbsp;&nbsp;&nbsp;&nbsp;1.3 Hypothesis ......................................................9

&nbsp;&nbsp;&nbsp;&nbsp;1.4 Methodology Overview ............................................9

&nbsp;&nbsp;&nbsp;&nbsp;1.5 Thesis Structure ...............................................10

**Chapter 2: Literature Review** .........................................11

&nbsp;&nbsp;&nbsp;&nbsp;2.1 Code Change Impact Analysis ....................................11

&nbsp;&nbsp;&nbsp;&nbsp;2.2 Static Analysis and Call Graphs for C ...........................12

&nbsp;&nbsp;&nbsp;&nbsp;2.3 Large Language Models for Code .................................13

&nbsp;&nbsp;&nbsp;&nbsp;2.4 Tool Use and Agent-Based Reasoning .............................14

&nbsp;&nbsp;&nbsp;&nbsp;2.5 Research Gap ...................................................15

**Chapter 3: System Design and Implementation** ..........................16

&nbsp;&nbsp;&nbsp;&nbsp;3.1 Architecture Overview ..........................................16

&nbsp;&nbsp;&nbsp;&nbsp;3.2 Call Graph Construction ........................................17

&nbsp;&nbsp;&nbsp;&nbsp;3.3 Friend 1 - Baseline LLM Approach ...............................18

&nbsp;&nbsp;&nbsp;&nbsp;3.4 Friend 2 - Call Graph-Augmented Approach .......................19

&nbsp;&nbsp;&nbsp;&nbsp;3.5 Friend 3 - Interactive Agent Approach ...........................20

&nbsp;&nbsp;&nbsp;&nbsp;3.6 Caching and Incremental Updates ................................21

&nbsp;&nbsp;&nbsp;&nbsp;3.7 VS Code Extension .............................................22

**Chapter 4: Experimental Setup** ........................................23

&nbsp;&nbsp;&nbsp;&nbsp;4.1 Dataset .......................................................23

&nbsp;&nbsp;&nbsp;&nbsp;4.2 Ground Truth Construction ......................................24

&nbsp;&nbsp;&nbsp;&nbsp;4.3 Evaluation Metrics ............................................25

&nbsp;&nbsp;&nbsp;&nbsp;4.4 Models and API Configuration ..................................25

**Chapter 5: Results and Analysis** ......................................26

&nbsp;&nbsp;&nbsp;&nbsp;5.1 Quantitative Results ..........................................26

&nbsp;&nbsp;&nbsp;&nbsp;5.2 Error Analysis ................................................28

&nbsp;&nbsp;&nbsp;&nbsp;5.3 Discussion ....................................................30

**Chapter 6: Conclusion** ................................................32

&nbsp;&nbsp;&nbsp;&nbsp;6.1 Summary of Contributions ......................................32

&nbsp;&nbsp;&nbsp;&nbsp;6.2 Limitations ...................................................33

&nbsp;&nbsp;&nbsp;&nbsp;6.3 Future Work ...................................................34

References ..............................................................36

---

<!-- PAGE 6: LIST OF FIGURES (short page, leads into Chapter 1) -->

## List of Figures

Figure 3.1 - Overall architecture of GraphGuard ........................17

Figure 3.2 - Example call graph for the demo banking project ............18

Figure 3.3 - Friend 1 prompt structure .................................19

Figure 3.4 - Friend 2 prompt structure with call graph context ..........20

Figure 3.5 - Friend 3 agent loop sequence diagram ......................21

Figure 4.1 - Distribution of project sizes in the dataset ...............24

Figure 5.1 - F1 scores per project, all three approaches ................27

Figure 5.2 - Precision-recall curves for Friend 1 and Friend 2 ..........28

Figure 5.3 - Token usage breakdown by approach .........................29

---

<!-- PAGES 6-10: CHAPTER 1 - INTRODUCTION (~1,400 words) -->

## Chapter 1: Introduction

### 1.1 Problem Statement

When a developer changes a function in a C codebase, a natural question follows: what else might break? In a small project with a few hundred lines of code, a developer can usually answer this from memory. In a project with tens of thousands of lines spread across many files, the question becomes genuinely difficult. A change to a low-level utility function can cascade through many layers of the call hierarchy and affect modules the developer never thought to check.

This problem - determining which parts of a software system are affected by a code change - is called code change impact analysis (CIA). It has practical consequences: developers who miss affected functions during code review may introduce regressions that only surface after merging or during production incidents. Thorough impact analysis requires either deep knowledge of the codebase or dedicated tooling to trace call relationships and dependencies.

Traditional static analysis tools do exist for this purpose. Tools like GNU cflow and Understand can build call graphs and trace dependencies in C programs. However, they have seen limited adoption outside of safety-critical and embedded development contexts. The main barriers are setup complexity, the need to integrate them into a build system, and the learning curve for interpreting results. Many developers working on open-source C projects do not use any CIA tool at all.

Large language models have changed expectations around what developers can ask a computer to help with. A developer can now describe a bug in natural language and get a plausible explanation. They can paste a function and ask what it does. A natural extension of this is to paste a diff and ask: what else in this codebase will this change affect? This requires no special tooling and can be done through a chat interface or IDE assistant.

The problem is that an LLM, given only a diff, cannot know what calls what in a specific project. It can recognize patterns - a function named `handle_error` probably affects error handling paths, a function that modifies a shared struct probably affects code that reads that struct - but it cannot trace the actual call graph of the project. Two projects might have completely different call structures for functions with identical names. Without seeing those relationships, the LLM's predictions are closer to informed guesses than structural reasoning.

This thesis investigates what happens when an LLM is given that structural information. The hypothesis is that providing a call graph context - specifically, which functions call the changed function, and which functions those callers call - will substantially improve prediction quality. We build a tool called GraphGuard that automates this process, and we evaluate it across 50 open-source C projects.

### 1.2 Research Objectives

This thesis has three main objectives. The first is to build a tool that is practical and usable - not a research prototype that requires a computer science background to operate, but something a developer can run from a terminal or click in an IDE sidebar. This means handling real-world complications: projects that use non-standard LLVM installations, projects with multiple source directories, and the need to rebuild the call graph only when files actually change.

The second objective is to quantify the difference between providing only the diff versus providing call graph context. We do this with a controlled comparison across 50 projects, using the same LLM model for both approaches and the same evaluation protocol. Precision, recall, and F1 score over the set of affected functions serve as the primary metrics.

The third objective is to explore agent-based analysis as an alternative to static context provision. In the agent approach, the LLM is given a set of tools - find callers, find callees, read function source, search for patterns - and can query the call graph interactively as it reasons. This mirrors how a developer would investigate the issue manually, and it may handle cases where the relevant context is too large to include upfront.

### 1.3 Hypothesis

The main hypothesis is that providing call graph context to an LLM substantially improves its accuracy on code change impact analysis compared to providing only the diff. Specifically, we expect both precision and recall to improve, because the LLM will have access to the actual call relationships in the project rather than relying on naming patterns and general programming knowledge.

A secondary hypothesis is that the agent-based approach performs at least as well as the static context approach on the test set, and that it will perform better on larger projects where the full context cannot be included in a single prompt.

### 1.4 Methodology Overview

GraphGuard is implemented in Python. It parses C source files using libclang, the C-family frontend of the LLVM compiler infrastructure, to extract function definitions and call relationships. From these, it constructs a directed call graph where each node is a function and each edge represents a direct call. The graph is serialized to disk and loaded on subsequent runs, with modification time checks to trigger rebuilds when source files change.

To find the changed functions for a given analysis run, GraphGuard calls `git diff` on the working tree, parses the output to identify which functions were modified, and then uses the call graph to find what is reachable from those functions through caller relationships.

For evaluation, we built a dataset of 50 open-source C projects ranging from small single-file utilities to medium-sized codebases with around fifteen thousand lines of code. For each project, we identified a set of representative commits - choosing commits that modified between one and five functions, which is typical for a focused change. We used the call graph computed from the commit's parent state to derive ground truth: the set of all functions that transitively call any of the modified functions is what a perfect impact analysis would report as affected.

All three approaches - the baseline (Friend 1), the call graph-augmented approach (Friend 2), and the agent (Friend 3) - are asked the same question: given this diff, which functions in this project are likely to be affected? Their outputs are lists of function names, which we compare against the ground truth using standard precision, recall, and F1 metrics.

### 1.5 Thesis Structure

Chapter 2 reviews related work on code change impact analysis, static call graph construction for C, large language models applied to code tasks, and agent-based approaches to tool use. Chapter 3 describes the design and implementation of GraphGuard, covering all three analysis approaches and the VS Code extension built on top of the core tool. Chapter 4 describes the experimental setup in detail. Chapter 5 presents results and analysis. Chapter 6 concludes with a summary, limitations, and directions for future work.

---

<!-- PAGES 11-14: CHAPTER 2 - LITERATURE REVIEW (~1,250 words) -->

## Chapter 2: Literature Review

### 2.1 Code Change Impact Analysis

The problem of determining what a code change affects has been studied in software engineering since at least the early 1990s. Lehnert (2011) provides a comprehensive survey of the field. His taxonomy distinguishes between static approaches, which analyze code structure without executing it, and dynamic approaches, which trace execution paths through instrumentation or test runs. Static approaches are faster and require no working test suite, but they may include call paths that are never actually exercised at runtime. Dynamic approaches are more precise but depend on the quality of the available test coverage.

Early static CIA tools were rooted in structured design methods. Bohner and Arnold (1996) surveyed industry practice and found that most change impact work was done manually, with developers relying on code knowledge and documentation. They argued for more systematic dependency analysis and proposed a taxonomy of software relationships relevant to CIA. Their framework distinguished syntactic dependencies - direct function calls, variable references - from semantic dependencies, which are harder to capture automatically.

For source-code-level analysis, the dominant approach has been to build a dependency graph - a graph where nodes are software entities (functions, modules, variables) and edges represent "depends on" relationships - and then compute the transitive closure of that graph from the changed entities. Functions or modules that are reachable from the changed code through the dependency edges are flagged as potentially affected.

Subsequent work refined this basic approach in several directions. Arnold and Bohner (1993) investigated dependency types and how to extract them from C source code. Reps, Horwitz, and Sagiv (1995) developed program slicing algorithms that are closely related to CIA - a backward slice of a program point captures all statements that could affect the value at that point, which is analogous to finding all callers in the impact analysis sense. These algorithms are well-studied and form the theoretical foundation for many commercial static analysis tools.

The challenge in applying these methods to C is the presence of function pointers. Unlike Java or C++, C has no method dispatch mechanism that can be statically resolved - any function pointer could in principle point to any compatible function. Practical call graph construction for C programs therefore accepts some imprecision, either by ignoring function pointer targets (potentially missing impact paths) or by including all reachable functions as possible targets (potentially over-approximating impact).

### 2.2 Static Analysis and Call Graphs for C

LibClang is the C and C++ frontend of the LLVM compiler infrastructure, exposed as a stable C API with bindings in multiple languages including Python. Unlike parsing with regular expressions or simple text processing, libclang produces a full abstract syntax tree (AST) that respects preprocessor macros, handles complex type expressions, and correctly deals with all legal C syntax. For the purpose of extracting function definitions and call sites, the Python `clang` bindings provide a straightforward tree traversal interface.

Several tools have offered call graph generation for C as a built-in feature. GNU cflow (Meyering, 1997) generates call graphs from C source files and has been part of the GNU project for decades. It is simple to use but does not handle some modern C constructs well. Doxygen (van Heesch, 1997), primarily a documentation generator, includes optional call graph output using the Graphviz library, but it requires significant configuration and is primarily aimed at generating visual diagrams rather than programmatic analysis. Understand from Scientific Toolworks is a commercial tool with precise call graph analysis capabilities, but its cost puts it out of reach for many open-source projects.

More recent work has used Joern (Yamaguchi et al., 2014), a code analysis platform that builds a code property graph combining the AST, control flow graph, and program dependency graph. Joern supports C and C++ and has been widely used in security research for vulnerability analysis. Its call graph capabilities are more complete than libclang-based approaches because it handles more edge cases, but it requires a separate installation and has a steeper learning curve.

GraphGuard's call graph module is simpler than any of these. It handles direct function calls correctly, skips indirect calls through function pointers, and is designed to be fast enough that rebuilding the graph for a medium-sized project takes only a few seconds. This tradeoff is deliberate - the goal is a tool that works reliably in a development workflow, not a research-grade static analyzer.

### 2.3 Large Language Models for Code

The publication of Codex (Chen et al., 2021) marked the beginning of serious interest in applying large language models to programming tasks. Codex was a GPT-3 variant fine-tuned on public code from GitHub, and it demonstrated that a language model could generate functionally correct code from natural language descriptions at a level that passed automated test suites. The HumanEval benchmark introduced in that paper has since become a standard evaluation for code generation.

Since Codex, code capability has become a standard feature of frontier language models. GPT-4 (OpenAI, 2023), Claude (Anthropic, 2023), and Gemini (Google, 2024) all show strong performance on code benchmarks, and specialized code models like DeepSeek-Coder (Guo et al., 2024) and CodeLlama (Roziere et al., 2023) push performance further by training specifically on code data. These models can explain code, identify bugs, suggest refactors, and complete partial implementations.

The application of LLMs to software engineering tasks beyond code generation has been an active research area. Prenner and Robbes (2021) evaluated early GPT models on bug detection and found promising results for simple defects. Kochhar et al. (2016) studied automated program repair with a focus on what kinds of bugs are amenable to automated fixing - a closely related problem to impact analysis in that both require reasoning about code structure and semantics. Schafer et al. (2023) evaluated LLMs on test generation and found that models with more context about the function under test produced better tests.

For impact analysis specifically, the literature is sparse. White et al. (2023) surveyed applications of ChatGPT to software engineering and mentioned impact analysis informally, noting that the model could identify obvious impact paths but struggled with project-specific relationships. Ni et al. (2023) studied LLM performance on various code understanding tasks and found that models often relied on surface-level patterns rather than structural reasoning. Both observations are consistent with our expectation that structural context will help.

### 2.4 Tool Use and Agent-Based Reasoning

The ability to call external tools during generation has substantially expanded what language models can do in practice. Schick et al. (2023) introduced Toolformer, a model that learned to insert API calls into its own generated text by fine-tuning on self-generated examples. More recently, OpenAI's function calling feature and Anthropic's tool use API provide a standard mechanism: the model is given a set of tool schemas in JSON format, it requests tool calls in its output, an external system executes those calls, and the results are fed back to continue generation.

The ReAct framework (Yao et al., 2022) demonstrated that interleaving reasoning and action - generating a thought, then an action, then observing the result, then reasoning again - outperforms either pure chain-of-thought reasoning or pure action sequences on tasks that require retrieving information from external sources. ReAct has influenced many subsequent agent frameworks and is the conceptual basis for Friend 3's agent loop.

For code tasks, agent-based approaches have shown impressive results on complex multi-step problems. SWE-agent (Yang et al., 2024) applies a language model agent to GitHub issues, letting the agent edit files, run tests, and navigate codebases to produce patches. The agent achieves competitive results on the SWE-bench benchmark. Devin (Cognition, 2024) takes a similar approach with a broader set of developer actions. Both systems highlight that interactive exploration - rather than reasoning from a fixed context window - is often more effective for tasks that require understanding a specific codebase.

### 2.5 Research Gap

The work reviewed in this chapter falls into two separate streams. On one side, code change impact analysis has decades of theoretical and tool development behind it, but has not been connected to modern LLM capabilities. On the other side, LLMs for code are well-studied for generation and summarization tasks, but rarely evaluated on impact analysis, and when they are, they receive only the changed code rather than structural program context.

This thesis connects these streams. We evaluate, specifically for C projects, whether providing LLM impact analysis with call graph context - the kind of structural information that traditional CIA tools are built around - improves prediction quality. We also compare static context provision against an agent approach where the LLM queries the call graph interactively. To our knowledge, this combination has not been studied in prior published work.

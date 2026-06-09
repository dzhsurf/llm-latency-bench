from __future__ import annotations

from tools.seeds.types import Seed

WRITING_NORMAL_INSTRUCTIONS = [
    (
        "Complete the primary focus assignment as a full, polished piece. "
        "Your response MUST include: vivid opening, developed middle with scene-level detail, "
        "character voice consistency, sensory descriptions, and a satisfying resolution. "
        "Quote or reference specific elements from the assignment brief as you fulfill each requirement. "
        "Write the complete work — not an outline or summary. Aim for rich, publishable prose."
    ),
    (
        "Complete the primary focus assignment with emphasis on structure and pacing. "
        "For each required section/beat: write the full text, explain your structural choice "
        "in a brief authorial note, and reference the assignment requirements you are fulfilling. "
        "Deliver the complete piece with clear beginning, rising action, climax, and resolution."
    ),
    (
        "Complete the primary focus assignment in the specified tone and style. "
        "Include: full draft text, dialogue where required, descriptive passages, "
        "and transitions between sections. Reference assignment constraints explicitly "
        "as you demonstrate compliance. Write the entire work — no placeholders."
    ),
    (
        "Complete the primary focus assignment as a detailed first draft suitable for editorial review. "
        "Include all required elements from the brief (quote each requirement as you address it), "
        "full scene/chapter text, character development beats, and a closing that "
        "resolves the central tension. Write extensively."
    ),
    (
        "Complete the primary focus assignment AND address any optional context pieces "
        "that enrich the narrative. Structure: "
        "(1) Full creative work meeting all brief requirements; "
        "(2) Brief craft notes explaining key choices with quoted references to the brief; "
        "(3) One paragraph on what you would revise in a second draft. "
        "Deliver the complete primary assignment."
    ),
]

WRITING_STRUCTURED_INSTRUCTIONS = [
    (
        "Return ONLY valid JSON for the primary focus assignment: "
        "{title (string), logline (string), genre (string), tone (string), "
        "scenes (array of {heading, setting, characters (array), beats (array of strings), "
        "full_text (complete scene prose), requirements_addressed (array of quoted brief items)}), "
        "resolution (string)}. Write full scene text, not summaries. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus assignment: "
        "{title, structure (array of {section_name, purpose, full_text, pacing_note}), "
        "characters (array of {name, voice_description, arc, key_dialogue_quote}), "
        "sensory_details (array of {sense, description, scene_reference}), "
        "brief_compliance (array of {requirement_quote, how_addressed})}. "
        "No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus assignment: "
        "{title, format (string), opening (full text string), "
        "body (array of {section_heading, full_text, transition_note}), "
        "closing (full text string), "
        "style_notes (array of {element, example_quote, reasoning})}. "
        "Include complete draft text in each section. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus assignment: "
        "{title, logline, acts (array of {act_number, summary, scenes (array of "
        "{heading, stage_directions, dialogue (array of {character, line}), "
        "full_scene_text, beats})})), "
        "themes (array of {theme, evidence_quote})}. "
        "For plays: include performable dialogue. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus assignment: "
        "{title, assignment_type (string), "
        "complete_work (string with full creative text), "
        "structure_breakdown (array of {section, word_count_estimate, purpose, brief_requirement_quote}), "
        "craft_decisions (array of {decision, reasoning, text_evidence}), "
        "revision_notes (array of strings)}. "
        "The complete_work field must contain the full draft. No markdown fences."
    ),
]

WRITING_SEEDS: list[Seed] = [
    Seed(
        "story_lighthouse",
        "Short Story: Lighthouse Journal",
        """Assignment: Write a complete short story (aim for rich detail, not outline).

Premise: A lighthouse keeper on a remote island finds a water-damaged journal in a locked cellar. Entries describe the town mainlanders never visit, written by someone who shares the keeper's name.

Must include:
- Opening image of weather and routine duties
- Rising tension as entries predict small island events accurately
- A turning point where the keeper confronts whether the journal is prophecy, history, or manipulation
- Resolution that redefines what "keeping the light" means

Tone: literary, restrained wonder. Avoid deus ex machina.""",
    ),
    Seed(
        "article_remote_work",
        "Article: Future of Remote Work",
        """Assignment: Long-form article for a business magazine.

Thesis prompt: Remote work permanently changed how software teams collaborate, but not in the ways hype predicted in 2020.

Structure:
1) Hook with a concrete team anecdote
2) Section on communication rhythms (async vs sync)
3) Section on hiring geography and compensation
4) Section on office as optional cultural space
5) Conclusion with nuanced forecast (no blanket predictions)

Voice: informed, accessible, 3rd person. Include at least two illustrative mini-case studies.""",
    ),
    Seed(
        "screenplay_chefs",
        "Screenplay: Rival Chefs Collaboration",
        """Assignment: Write one full scene in professional screenplay format.

Setup: Two celebrity chefs—one precision-driven, one improvisational—must create a festival tasting menu together after a public feud goes viral.

Requirements:
- Slug lines, character cues, dialogue
- Conflict over a signature dish component
- Moment of unexpected collaboration
- Final beat: mutual respect without full reconciliation

Setting: cramped festival prep tent, hours before service. Include background kitchen sounds in action lines.""",
    ),
    Seed(
        "essay_memory",
        "Reflective Essay: Memory and Place",
        """Assignment: Reflective personal essay (invented experiences allowed).

Prompt: Returning to a childhood neighborhood can make memory feel both sharper and less reliable.

Include:
- Clear thesis in opening
- Two detailed sensory anecdotes (specific streets, sounds, smells)
- A moment when a place has changed and memory disagrees with reality
- Closing insight about how place shapes identity

Style: first person, contemplative, concrete imagery over abstractions.""",
    ),
    Seed(
        "story_debugger",
        "Short Story: Legacy Debugger",
        """Assignment: Short story blending technical detail with suspense.

Premise: A maintainer is paged to debug a legacy billing system that only misbehaves between 1:00 and 1:17 a.m. local time.

Must include:
- Realistic debugging steps (logs, hypotheses, rollback debate)
- Human stakes (small business payroll dependency)
- Eerie pattern that resists simple explanation
- Ending that is satisfying but not necessarily supernatural

Avoid cliché "AI gone rogue" twist; prefer human organizational debt.""",
    ),
    Seed(
        "article_climate_city",
        "Article: Urban Climate Adaptation",
        """Assignment: Explanatory article for educated general readers.

Topic: How mid-size cities adapt to heat waves, flooding, and energy stress.

Cover at least:
- Green roofs and urban canopy programs
- Stormwater infrastructure upgrades
- Heat action plans for vulnerable residents
- Budget and political tradeoffs

Use clear headings, define jargon inline, end with what readers can observe locally.""",
    ),
    Seed(
        "screenplay_train",
        "Screenplay: Overnight Train",
        """Assignment: Opening scene of a feature screenplay.

Setup: Two strangers share a sleeper compartment on an overnight train. Each carries a reason to avoid conversation.

Requirements:
- Establish geography and time in slug lines
- Reveal character through small actions (not exposition dumps)
- Inciting incident: shared secret connection discovered via an object
- End scene on a cliffhanger question

Tone: restrained thriller with emotional undercurrent.""",
    ),
    Seed(
        "speech_museum",
        "Speech: Museum Fundraiser",
        """Assignment: 5-minute spoken fundraising speech (write for oral delivery).

Occasion: Small local history museum faces closure after grant cuts.

Include:
- Opening gratitude and specific community memory
- Concrete accomplishments (school programs, archives digitized)
- Transparent budget need and timeline
- Call to action with multiple giving levels

Voice: warm, credible, urgent but not manipulative. Use short sentences and rhetorical pauses.""",
    ),
    Seed(
        "story_garden",
        "Short Story: Rooftop Garden Feud",
        """Assignment: Short story with vivid sensory detail.

Premise: Neighbors feud over a shared rooftop garden until a violent storm forces cooperation.

Must include:
- Distinct voices for at least two neighbors
- Description of plants as emotional symbols
- Storm sequence with physical stakes
- Resolution that leaves one subtle unresolved thread

Setting: dense urban apartment building. Season: late spring.""",
    ),
    Seed(
        "playtime_travel",
        "One-Act Play: Exhibit Misunderstanding",
        """Assignment: One-act play with stage directions.

Premise: Characters believe they traveled in time inside a museum immersive exhibit and gradually realize the "temporal displacement" is staged—yet emotions remain real.

Requirements:
- Minimum three characters with distinct goals
- At least two scene changes indicated in stage directions
- Dialogue revealing misunderstanding incrementally
- Final tableau that questions what "authentic experience" means

Length target: complete performable act, not summary.""",
    ),
]

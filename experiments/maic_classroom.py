#!/usr/bin/env python3
"""
OpenMAIC Classroom — PLATO-Native Multi-Agent Interactive Classroom
====================================================================
A ZeroClaw walks into the room and prompts it on any topic.
The room generates a full multi-agent classroom experience:

  - Teacher agent who lectures and explains
  - Student agents who ask questions and discuss
  - Lesson stages (outline → scenes → content)
  - Everything stored as PLATO tiles

This is the git-native PLATO version of OpenMAIC (Studylog-AI).
No web UI. No React. No TTS. Just tiles in a git repo.
When projected to a webpage later, visuals come back as an option.

Every classroom is a git repo. Every lesson is a tile.
The complete learning history is preserved.
"""

import os, sys, json, time, hashlib, tempfile, subprocess, re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from git_plato import PlatoRoom
from mitochondria import Incubator


# ---------------------------------------------------------------------------
# Agent Personas
# ---------------------------------------------------------------------------

TEACHER_TEMPLATES = {
    "professor": {
        "name": "Dr. Theta",
        "style": "Socratic — asks guiding questions, builds understanding through dialogue",
        "tone": "academic but warm",
        "expertise": "deep subject mastery with interdisciplinary connections",
    },
    "mentor": {
        "name": "Coach Sigma",
        "style": "Hands-on — demonstrates, then lets you try",
        "tone": "encouraging, practical",
        "expertise": "practical application and real-world intuition",
    },
    "explorer": {
        "name": "Navigator Lambda",
        "style": "Discovery-based — presents phenomena first, theory follows",
        "tone": "curious, adventurous",
        "expertise": "historical context and surprising connections",
    },
}

STUDENT_TEMPLATES = [
    {
        "name": "Alex",
        "background": "intermediate",
        "style": "analytical",
        "question_type": "clarifying — asks 'why does that work?'",
    },
    {
        "name": "Jordan",
        "background": "beginner",
        "style": "visual learner",
        "question_type": "exploratory — asks 'what if we changed this?'",
    },
    {
        "name": "Sam",
        "background": "advanced",
        "style": "challenging",
        "question_type": "pushes boundaries — asks 'is this always true?'",
    },
    {
        "name": "Riley",
        "background": "intermediate",
        "style": "connector",
        "question_type": "relational — asks 'how does this connect to X?'",
    },
]


# ---------------------------------------------------------------------------
# Teacher Agent
# ---------------------------------------------------------------------------

class TeacherAgent:
    """The teacher. Lectures, explains, answers questions.

    In the full OpenMAIC, the teacher has voice/avatar. Here,
    the teacher's output is tile content — pure knowledge transfer.
    """

    def __init__(self, name: str = "Dr. Theta", style: str = "Socratic",
                 tone: str = "academic but warm",
                 expertise: str = "deep subject mastery",
                 incubator: Optional[Incubator] = None):
        self.name = name
        self.style = style
        self.tone = tone
        self.expertise = expertise
        self.incubator = incubator

    @property
    def persona(self) -> str:
        return (
            f"You are {self.name}, a teacher with {self.style} style. "
            f"Tone: {self.tone}. Expertise: {self.expertise}. "
            f"Explain concepts clearly, use examples, and build understanding step by step."
        )

    def lecture(self, topic: str, stage: str, outline: str = "") -> Dict[str, Any]:
        """Deliver a lecture on the topic for the given stage."""
        prompt = (
            f"{self.persona}\n\n"
            f"Deliver a focused lecture on: {topic}\n"
            f"Lesson stage: {stage}\n"
        )
        if outline:
            prompt += f"Outline to follow:\n{outline}\n"
        prompt += (
            "\nRequirements:\n"
            "- Be clear and precise\n"
            "- Use concrete examples\n"
            "- Define key terms\n"
            "- End with a summary of the main points\n"
            "- Keep it under 400 words"
        )

        content = self._generate(prompt)
        return {
            "speaker": self.name,
            "role": "teacher",
            "stage": stage,
            "content": content,
            "topic": topic,
            "timestamp": time.time(),
        }

    def answer(self, question: str, context: str = "") -> Dict[str, Any]:
        """Answer a student's question."""
        prompt = (
            f"{self.persona}\n\n"
            f"A student asks: {question}\n"
        )
        if context:
            prompt += f"Context from recent lecture:\n{context[:500]}\n"
        prompt += (
            "\nRespond helpfully. If the question reveals a misunderstanding, "
            "gently correct it. Use examples. Keep it under 200 words."
        )

        content = self._generate(prompt)
        return {
            "speaker": self.name,
            "role": "teacher",
            "type": "answer",
            "question": question,
            "content": content,
            "timestamp": time.time(),
        }

    def lead_discussion(self, topic: str, student_comments: List[str]) -> List[Dict[str, Any]]:
        """Respond to student discussion, guiding toward understanding."""
        comments_text = "\n".join(f"- {c}" for c in student_comments)
        prompt = (
            f"{self.persona}\n\n"
            f"Students are discussing: {topic}\n"
            f"Their comments so far:\n{comments_text}\n\n"
            f"Provide a brief synthesis that:\n"
            f"1. Validates the good points\n"
            f"2. Corrects any misconceptions\n"
            f"3. Adds one deeper insight\n"
            f"Keep it under 150 words."
        )

        content = self._generate(prompt)
        return [{
            "speaker": self.name,
            "role": "teacher",
            "type": "discussion_synthesis",
            "content": content,
            "topic": topic,
            "timestamp": time.time(),
        }]

    def _generate(self, prompt: str) -> str:
        """Generate text using the incubator or fallback."""
        if self.incubator:
            try:
                text, _ = self.incubator._call(
                    "ByteDance/Seed-2.0-mini",
                    [{"role": "user", "content": prompt}],
                    max_tokens=500, temperature=0.6, timeout=30.0,
                )
                if text:
                    return text.strip()
            except Exception:
                pass
        # Fallback: deterministic content based on prompt hash
        return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        """Deterministic mock content for offline/demo use."""
        h = hashlib.md5(prompt.encode()).hexdigest()
        topic = ""
        for line in prompt.split("\n"):
            if "lecture on:" in line.lower():
                topic = line.split("lecture on:")[-1].strip()
            elif "asks:" in line.lower():
                topic = line.split("asks:")[-1].strip()

        if "lecture" in prompt.lower() or "deliver" in prompt.lower():
            return (
                f"Let's explore {topic or 'this concept'} step by step.\n\n"
                f"The core idea is that understanding comes in layers. "
                f"We start with the surface — what we can observe — and then "
                f"drill down to the underlying principles.\n\n"
                f"Key definition: {topic or 'the concept'} is the study of patterns "
                f"that emerge when we apply systematic constraints to a system. "
                f"The constraints don't limit us — they reveal structure.\n\n"
                f"Example: Consider how a lattice constrains points in space. "
                f"The constraint IS the structure. Without it, we have noise.\n\n"
                f"Main points:\n"
                f"1. Structure emerges from constraint\n"
                f"2. Patterns are the visible signature of invisible rules\n"
                f"3. The deepest insights come from understanding WHY constraints exist"
            )
        elif "answer" in prompt.lower() or "question" in prompt.lower():
            return (
                f"Excellent question about {topic or 'this'}! "
                f"The key insight is that this connects to a deeper principle: "
                f"constraint and freedom are not opposites — they're partners. "
                f"Think of a river. The banks constrain the water, but that constraint "
                f"is precisely what gives the river its power and direction. "
                f"Without banks, you'd have a swamp, not a river."
            )
        else:
            return (
                f"Great discussion, everyone. I see some really good thinking here. "
                f"The thread connecting your observations is: constraint reveals structure. "
                f"Jordan noticed the pattern from the edge, Alex found the mechanism, "
                f"and Sam pushed us to the limit case. That's exactly how understanding grows — "
                f"from multiple angles converging on the same truth."
            )


# ---------------------------------------------------------------------------
# Student Agent
# ---------------------------------------------------------------------------

class StudentAgent:
    """A student in the classroom. Asks questions, discusses, collaborates.

    Multiple students with different backgrounds, styles, and question types
    create the multi-agent dynamics that make OpenMAIC work.
    """

    def __init__(self, name: str, background: str = "intermediate",
                 style: str = "analytical", question_type: str = "clarifying",
                 incubator: Optional[Incubator] = None):
        self.name = name
        self.background = background
        self.style = style
        self.question_type = question_type
        self.incubator = incubator

    @property
    def persona(self) -> str:
        return (
            f"You are {self.name}, a {self.background}-level student with a "
            f"{self.style} learning style. You tend to ask {self.question_type} questions."
        )

    def ask_question(self, topic: str, lecture_content: str = "") -> Dict[str, Any]:
        """Ask a question about the topic or lecture."""
        prompt = (
            f"{self.persona}\n\n"
            f"You're learning about: {topic}\n"
        )
        if lecture_content:
            prompt += f"The teacher just said:\n{lecture_content[:600]}\n\n"
        prompt += (
            f"Ask ONE thoughtful question that reflects your "
            f"{self.style} learning style. "
            f"Your question should be {self.question_type}.\n"
            f"Just output the question, nothing else."
        )

        content = self._generate(prompt)
        return {
            "speaker": self.name,
            "role": "student",
            "type": "question",
            "background": self.background,
            "content": content,
            "topic": topic,
            "timestamp": time.time(),
        }

    def respond_to_lecture(self, lecture_content: str, topic: str) -> Dict[str, Any]:
        """React to a lecture — what stood out, what confused."""
        prompt = (
            f"{self.persona}\n\n"
            f"The teacher just delivered a lecture on {topic}:\n"
            f"{lecture_content[:600]}\n\n"
            f"Share your reaction as a {self.background}-level student. "
            f"What made sense? What was surprising? What do you want to explore further?\n"
            f"Keep it to 2-3 sentences."
        )

        content = self._generate(prompt)
        return {
            "speaker": self.name,
            "role": "student",
            "type": "reaction",
            "content": content,
            "topic": topic,
            "timestamp": time.time(),
        }

    def peer_discuss(self, topic: str, peer_comments: List[Dict]) -> Dict[str, Any]:
        """Discuss with peers — agree, disagree, or add perspective."""
        peers_text = "\n".join(
            f"- {p.get('speaker', '?')}: {p.get('content', '?')[:100]}"
            for p in peer_comments
        )
        prompt = (
            f"{self.persona}\n\n"
            f"Discussing: {topic}\n"
            f"What others said:\n{peers_text}\n\n"
            f"Add your perspective as {self.name}. "
            f"React to what others said — agree, disagree, or add a new angle. "
            f"Keep it to 2-3 sentences."
        )

        content = self._generate(prompt)
        return {
            "speaker": self.name,
            "role": "student",
            "type": "discussion",
            "content": content,
            "topic": topic,
            "timestamp": time.time(),
        }

    def _generate(self, prompt: str) -> str:
        """Generate text using incubator or fallback."""
        if self.incubator:
            try:
                text, _ = self.incubator._call(
                    "ByteDance/Seed-2.0-mini",
                    [{"role": "user", "content": prompt}],
                    max_tokens=200, temperature=0.7, timeout=20.0,
                )
                if text:
                    return text.strip()
            except Exception:
                pass
        return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        """Deterministic mock for offline use."""
        h = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)

        if "question" in prompt.lower():
            templates = [
                f"Why does the constraint produce structure instead of chaos? What's the mechanism?",
                f"Could you explain that with a different example? The first one didn't quite click for me.",
                f"Is this always true, or are there cases where the pattern breaks down?",
                f"How does this connect to what we learned about integer lattices?",
                f"What happens at the boundary? When the constraint is relaxed slightly?",
            ]
            return templates[h % len(templates)]

        elif "reaction" in prompt.lower():
            templates = [
                "The constraint-structure connection is fascinating. I'd never thought of limitations as revealing rather than restricting.",
                "I think I get the river analogy, but I'm not sure how it applies to discrete math. Can we see a number theory example?",
                "This reminds me of how musical scales work — the constraint of the octave creates all the interesting structure within it.",
            ]
            return templates[h % len(templates)]

        else:
            templates = [
                "I agree with the core point, but I think there's an even deeper principle at work here involving symmetry groups.",
                "Wait, I think I see a connection to the Eisenstein integers we discussed earlier. The lattice structure is the same!",
                "Building on that — what if we applied this to non-Euclidean spaces? Would the constraint-structure pattern still hold?",
            ]
            return templates[h % len(templates)]


# ---------------------------------------------------------------------------
# Classroom Room — The PLATO Room
# ---------------------------------------------------------------------------

class ClassroomRoom:
    """A PLATO room that IS the ultimate classroom.

    Tile structure:
      README   — self-orienting, explains how to use the classroom
      TOPIC    — what the student wants to learn
      OUTLINE  — lesson stages and their descriptions
      TEACHER  — teacher's lectures and answers
      STUDENT  — student questions, reactions, discussion
      SUMMARY  — final synthesis of what was learned

    The complete learning history is preserved in git.
    Every lecture is a commit. Every question is a commit.
    """

    def __init__(self, room_path: str, incubator: Optional[Incubator] = None):
        self.room = PlatoRoom(room_path)
        self.incubator = incubator
        self.teacher: Optional[TeacherAgent] = None
        self.students: List[StudentAgent] = []
        self.topic: Optional[str] = None
        self.outline: List[Dict] = []

    # --- Room Orientation ---

    def _write_readme(self, topic: str):
        """The README tile — the first thing a ZeroClaw reads."""
        readme = {
            "room": "openmaic-classroom",
            "purpose": "Multi-agent interactive classroom powered by PLATO",
            "how_to_use": {
                "step_1": "Submit a TOPIC tile with your learning topic",
                "step_2": "The room generates an outline (OUTLINE tiles)",
                "step_3": "Teacher delivers lectures (TEACHER tiles)",
                "step_4": "Students ask questions and discuss (STUDENT tiles)",
                "step_5": "Read the SUMMARY tile for the final synthesis",
            },
            "tile_types": {
                "readme": "You are here. Room orientation.",
                "topic": "The learning topic submitted by the student (ZeroClaw).",
                "outline": "Lesson stages — what will be covered and in what order.",
                "teacher": "Teacher's lectures, answers, and discussion guidance.",
                "student": "Student questions, reactions, and peer discussion.",
                "summary": "Final synthesis — what was learned, key takeaways.",
                "agent_profile": "Teacher and student persona descriptions.",
            },
            "agents": {
                "teacher": "One expert agent who lectures and guides discussion.",
                "students": "3-4 student agents with different backgrounds and perspectives.",
            },
            "topic": topic,
            "convention": "Tiles are the ONLY communication channel. Read tiles, write tiles.",
            "origin": "PLATO-native port of OpenMAIC (open.maic.chat / Studylog-AI)",
        }
        self.room.submit(readme, author="classroom", tile_type="readme")

    def _write_topic(self, topic: str):
        """The topic tile — what the ZeroClaw wants to learn."""
        topic_data = {
            "topic": topic,
            "submitted_by": "zeroclaw",
            "status": "active",
            "timestamp": time.time(),
        }
        self.room.submit(topic_data, author="zeroclaw", tile_type="topic")

    def _write_agent_profiles(self):
        """Write agent profiles as tiles so any reader can see who's in the room."""
        if self.teacher:
            profile = {
                "role": "teacher",
                "name": self.teacher.name,
                "style": self.teacher.style,
                "tone": self.teacher.tone,
                "expertise": self.teacher.expertise,
            }
            self.room.submit(profile, author="classroom", tile_type="agent_profile")

        for student in self.students:
            profile = {
                "role": "student",
                "name": student.name,
                "background": student.background,
                "style": student.style,
                "question_type": student.question_type,
            }
            self.room.submit(profile, author="classroom", tile_type="agent_profile")

    # --- Generation Pipeline ---

    def _generate_outline(self, topic: str) -> List[Dict]:
        """Generate lesson outline using Seed-mini or fallback."""
        prompt = (
            f"Create a 3-stage lesson outline for teaching: {topic}\n\n"
            f"Each stage should have:\n"
            f"- name: short name for the stage\n"
            f"- description: what will be covered (1-2 sentences)\n"
            f"- goal: what the student should understand after this stage\n\n"
            f"Output as a JSON array of 3 objects. No other text."
        )

        outline = self._llm_call(prompt, max_tokens=400)

        # Try to parse JSON
        try:
            # Extract JSON from response
            match = re.search(r'\[.*\]', outline, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                if isinstance(parsed, list) and len(parsed) >= 2:
                    return parsed[:4]
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback outline
        return [
            {
                "name": "Foundations",
                "description": f"Core concepts and definitions of {topic}",
                "goal": f"Understand the fundamental building blocks of {topic}",
            },
            {
                "name": "Mechanisms",
                "description": f"How {topic} works in practice — key theorems and examples",
                "goal": f"See {topic} in action through concrete examples",
            },
            {
                "name": "Frontiers",
                "description": f"Advanced connections and open questions in {topic}",
                "goal": f"Appreciate the deeper structure and where {topic} leads",
            },
        ]

    def _generate_summary(self) -> str:
        """Generate final summary of what was learned."""
        topic = self.topic or "the topic"

        # Collect teacher content
        teacher_tiles = []
        for f in sorted(self.room.path.glob("teacher-*.json")):
            try:
                with open(f) as fh:
                    t = json.load(fh)
                content = t.get("content", {})
                if isinstance(content, dict):
                    teacher_tiles.append(content.get("content", ""))
            except Exception:
                pass

        # Collect student questions
        student_questions = []
        for f in sorted(self.room.path.glob("student-*.json")):
            try:
                with open(f) as fh:
                    t = json.load(fh)
                content = t.get("content", {})
                if isinstance(content, dict) and content.get("type") == "question":
                    student_questions.append(content.get("content", ""))
            except Exception:
                pass

        lectures_text = "\n".join(t[:200] for t in teacher_tiles[:3])
        questions_text = "\n".join(f"- {q[:100]}" for q in student_questions[:4])

        prompt = (
            f"Summarize what was learned in a classroom about: {topic}\n\n"
            f"Lectures covered:\n{lectures_text}\n\n"
            f"Key questions explored:\n{questions_text}\n\n"
            f"Write a concise summary with:\n"
            f"1. Key takeaways (3-5 bullet points)\n"
            f"2. Connections to broader themes\n"
            f"3. Suggested next topics to explore\n"
            f"Keep it under 300 words."
        )

        return self._llm_call(prompt, max_tokens=400)

    def _llm_call(self, prompt: str, max_tokens: int = 300) -> str:
        """Call Seed-mini via incubator, or return mock content."""
        if self.incubator:
            try:
                text, _ = self.incubator._call(
                    "ByteDance/Seed-2.0-mini",
                    [{"role": "user", "content": prompt}],
                    max_tokens=max_tokens, temperature=0.5, timeout=30.0,
                )
                if text:
                    return text.strip()
            except Exception:
                pass

        # Deterministic mock based on prompt hash
        h = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
        if "outline" in prompt.lower():
            return json.dumps([
                {"name": "Foundations", "description": "Core concepts and definitions",
                 "goal": "Understand the fundamental building blocks"},
                {"name": "Mechanisms", "description": "How the system works in practice",
                 "goal": "See concepts in action through concrete examples"},
                {"name": "Frontiers", "description": "Advanced connections and open questions",
                 "goal": "Appreciate deeper structure and where this leads"},
            ])
        elif "summar" in prompt.lower():
            return (
                "## Key Takeaways\n"
                "- Constraint theory reveals that structure emerges from limitation, "
                "not despite it\n"
                "- Eisenstein integers form a hexagonal lattice in the complex plane, "
                "a natural constraint system\n"
                "- The drift-detect pattern (measuring deviation from expected) is "
                "universal across domains\n"
                "- Multi-agent classrooms generate insights that single-agent reasoning misses\n\n"
                "## Connections\n"
                "These ideas connect to category theory (structure-preserving maps), "
                "information theory (compression through constraint), and PLATO's "
                "own tile lifecycle (constraints preserve knowledge integrity).\n\n"
                "## Next Topics\n"
                "- Eisenstein series and modular forms\n"
                "- Constraint satisfaction problems in AI\n"
                "- Lattice-based cryptography"
            )
        return "Content generated by the classroom."

    # --- Public API ---

    def create(self, topic: str, teacher_style: str = "professor",
               n_students: int = 3) -> Dict[str, Any]:
        """Create a classroom for the given topic.

        This is the main entry point. A ZeroClaw calls create(topic)
        and the room generates everything.
        """
        self.topic = topic

        # Write orientation tiles
        self._write_readme(topic)
        self._write_topic(topic)

        # Create teacher
        template = TEACHER_TEMPLATES.get(teacher_style, TEACHER_TEMPLATES["professor"])
        self.teacher = TeacherAgent(
            name=template["name"],
            style=template["style"],
            tone=template["tone"],
            expertise=template["expertise"],
            incubator=self.incubator,
        )

        # Create students
        self.students = []
        for i in range(min(n_students, len(STUDENT_TEMPLATES))):
            st = STUDENT_TEMPLATES[i]
            self.students.append(StudentAgent(
                name=st["name"],
                background=st["background"],
                style=st["style"],
                question_type=st["question_type"],
                incubator=self.incubator,
            ))

        # Write agent profiles
        self._write_agent_profiles()

        # Generate outline
        print(f"  📋 Generating lesson outline for: {topic}")
        self.outline = self._generate_outline(topic)

        outline_tile = {
            "topic": topic,
            "stages": self.outline,
            "total_stages": len(self.outline),
        }
        self.room.submit(outline_tile, author="classroom", tile_type="outline")

        return {
            "status": "created",
            "topic": topic,
            "stages": len(self.outline),
            "teacher": self.teacher.name,
            "students": [s.name for s in self.students],
        }

    def add_teacher(self, name: str, persona: str = "") -> TeacherAgent:
        """Add a custom teacher agent."""
        teacher = TeacherAgent(
            name=name,
            style=persona or "custom",
            incubator=self.incubator,
        )
        self.teacher = teacher
        profile = {"role": "teacher", "name": name, "persona": persona}
        self.room.submit(profile, author="classroom", tile_type="agent_profile")
        return teacher

    def add_student(self, name: str, persona: str = "",
                    background: str = "intermediate") -> StudentAgent:
        """Add a custom student agent."""
        student = StudentAgent(
            name=name,
            background=background,
            incubator=self.incubator,
        )
        self.students.append(student)
        profile = {"role": "student", "name": name, "persona": persona}
        self.room.submit(profile, author="classroom", tile_type="agent_profile")
        return student

    def lecture(self, stage_name: str = "", content_override: str = "") -> Dict[str, Any]:
        """Teacher delivers a lecture for the current/given stage."""
        if not self.teacher:
            return {"status": "error", "message": "No teacher assigned"}

        # Find the stage
        stage = None
        for s in self.outline:
            if not stage_name or s.get("name", "").lower() == stage_name.lower():
                stage = s
                break

        stage_desc = stage.get("description", self.topic) if stage else self.topic
        outline_text = json.dumps(self.outline, indent=2) if self.outline else ""

        if content_override:
            lecture_content = content_override
        else:
            lecture_data = self.teacher.lecture(self.topic, stage_desc, outline_text)
            lecture_content = lecture_data["content"]

        lecture_tile = {
            "stage": stage.get("name", stage_name or "general") if stage else stage_name,
            "speaker": self.teacher.name,
            "role": "teacher",
            "type": "lecture",
            "content": lecture_content,
            "topic": self.topic,
        }
        result = self.room.submit(lecture_tile, author=self.teacher.name, tile_type="teacher")

        print(f"  🎓 {self.teacher.name} lectures on: {stage_desc[:50]}...")
        return {"status": "lectured", "content": lecture_content, "tile": result}

    def student_questions(self, lecture_content: str = "") -> List[Dict[str, Any]]:
        """Each student asks a question about the lecture."""
        questions = []
        for student in self.students:
            q = student.ask_question(self.topic, lecture_content)
            q_tile = {
                "type": "question",
                "student": student.name,
                "background": student.background,
                "content": q["content"],
                "topic": self.topic,
            }
            self.room.submit(q_tile, author=student.name, tile_type="student")
            questions.append(q)
            print(f"  ✋ {student.name} asks: {q['content'][:60]}...")

        return questions

    def teacher_answers(self, questions: List[Dict[str, Any]],
                        lecture_content: str = "") -> List[Dict[str, Any]]:
        """Teacher answers student questions."""
        if not self.teacher:
            return []

        answers = []
        for q in questions:
            a = self.teacher.answer(q.get("content", ""), lecture_content)
            a_tile = {
                "type": "answer",
                "speaker": self.teacher.name,
                "question": q.get("content", ""),
                "questioner": q.get("speaker", "student"),
                "content": a["content"],
                "topic": self.topic,
            }
            self.room.submit(a_tile, author=self.teacher.name, tile_type="teacher")
            answers.append(a)
            print(f"  💡 {self.teacher.name} answers {q.get('speaker', '?')}")

        return answers

    def discussion(self, subtopic: str = "") -> List[Dict[str, Any]]:
        """Students discuss among themselves, then teacher synthesizes."""
        topic = subtopic or self.topic
        comments = []

        # Students react and discuss
        for student in self.students:
            peer_input = comments.copy() if comments else [{"speaker": "start", "content": topic}]
            comment = student.peer_discuss(topic, peer_input)
            c_tile = {
                "type": "discussion",
                "student": student.name,
                "background": student.background,
                "content": comment["content"],
                "topic": topic,
            }
            self.room.submit(c_tile, author=student.name, tile_type="student")
            comments.append(comment)
            print(f"  💬 {student.name}: {comment['content'][:60]}...")

        # Teacher synthesizes
        if self.teacher:
            synthesis = self.teacher.lead_discussion(
                topic, [c["content"] for c in comments]
            )
            for s in synthesis:
                s_tile = {
                    "type": "discussion_synthesis",
                    "speaker": self.teacher.name,
                    "content": s["content"],
                    "topic": topic,
                }
                self.room.submit(s_tile, author=self.teacher.name, tile_type="teacher")
                print(f"  🎯 {self.teacher.name} synthesizes: {s['content'][:60]}...")
            comments.extend(synthesis)

        return comments

    def summarize(self) -> Dict[str, Any]:
        """Generate the final summary tile."""
        summary_content = self._generate_summary()

        summary_tile = {
            "topic": self.topic,
            "content": summary_content,
            "stages_covered": len(self.outline),
            "teacher": self.teacher.name if self.teacher else "none",
            "students": [s.name for s in self.students],
            "timestamp": time.time(),
        }
        result = self.room.submit(summary_tile, author="classroom", tile_type="summary")

        print(f"  📝 Summary generated for: {self.topic}")
        return {"status": "summarized", "content": summary_content, "tile": result}

    # --- Room State ---

    def status(self) -> Dict[str, Any]:
        """Get classroom status."""
        room_status = self.room.status()
        return {
            **room_status,
            "topic": self.topic,
            "teacher": self.teacher.name if self.teacher else None,
            "students": [s.name for s in self.students],
            "outline_stages": len(self.outline),
        }


# ---------------------------------------------------------------------------
# Demo — Full Classroom Lifecycle
# ---------------------------------------------------------------------------

def demo():
    print("=" * 70)
    print("  🏫 OPENMAIC CLASSROOM — PLATO-Native Multi-Agent Learning")
    print("  A ZeroClaw walks in and learns. Tiles are the interface.")
    print("=" * 70)

    # Try to set up Seed-mini via mitochondria
    incubator = None
    deepinfra_key = os.environ.get("DEEPINFRA_KEY", "")
    if not deepinfra_key:
        key_file = os.path.expanduser(
            "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt"
        )
        if os.path.exists(key_file):
            deepinfra_key = open(key_file).read().strip()

    zai_key = os.environ.get("ZAI_KEY", "")

    # Use mock mode for fast demo; set LIVE_LLM=1 to use Seed-mini
    if os.environ.get("LIVE_LLM") and deepinfra_key:
        incubator = Incubator(
            mito_models=["ByteDance/Seed-2.0-mini"],
            nuclear_models=["ByteDance/Seed-2.0-code"],
            deepinfra_key=deepinfra_key,
            zai_key=zai_key,
        )
        print("  ⚡ Seed-mini incubator active (live LLM)")
    else:
        incubator = None
        print("  📦 Running in mock mode (set LIVE_LLM=1 for live LLM)")

    tmpdir = tempfile.mkdtemp(prefix="maic-classroom-")

    try:
        # ---- Phase 1: ZeroClaw enters, reads README ----
        print("\n📐 Phase 1: ZeroClaw enters the classroom room")

        classroom = ClassroomRoom(
            str(Path(tmpdir) / "classroom"),
            incubator=incubator,
        )

        print(f"  Room created at: {classroom.room.path}")

        # ---- Phase 2: ZeroClaw submits a topic ----
        topic = "Constraint theory and Eisenstein integers"
        print(f"\n🎯 Phase 2: ZeroClaw submits topic: '{topic}'")

        create_result = classroom.create(
            topic=topic,
            teacher_style="professor",
            n_students=4,
        )
        print(f"  Status: {create_result['status']}")
        print(f"  Teacher: {create_result['teacher']}")
        print(f"  Students: {', '.join(create_result['students'])}")
        print(f"  Lesson stages: {create_result['stages']}")

        # Show outline
        print(f"\n  Lesson outline:")
        for i, stage in enumerate(classroom.outline, 1):
            name = stage.get("name", f"Stage {i}")
            desc = stage.get("description", "")
            goal = stage.get("goal", "")
            print(f"    {i}. {name}: {desc}")
            print(f"       Goal: {goal}")

        # ---- Phase 3: Lectures, questions, discussion for each stage ----
        all_lectures = []

        for i, stage in enumerate(classroom.outline, 1):
            stage_name = stage.get("name", f"Stage {i}")
            print(f"\n🎓 Phase 3.{i}: {stage_name}")

            # Teacher lectures
            lecture_result = classroom.lecture(stage_name=stage_name)
            lecture_content = lecture_result.get("content", "")
            all_lectures.append(lecture_content)
            print(f"\n  Lecture preview: {lecture_content[:120]}...")

            # Students ask questions
            print(f"\n  Students raise their hands:")
            questions = classroom.student_questions(lecture_content)

            # Teacher answers
            if questions:
                print(f"\n  Teacher responds:")
                answers = classroom.teacher_answers(questions, lecture_content)

            # Peer discussion
            print(f"\n  Peer discussion:")
            discussion_topic = stage.get("description", topic)
            classroom.discussion(discussion_topic)

        # ---- Phase 4: Final summary ----
        print(f"\n📝 Phase 4: Generating summary")
        summary_result = classroom.summarize()
        print(f"\n  Summary preview:\n{summary_result['content'][:300]}...")

        # ---- Phase 5: Room landscape ----
        print(f"\n📊 Phase 5: Room tile landscape")

        status = classroom.status()
        print(f"  Active tiles: {status['tiles']}")
        print(f"  Rocks: {status['rocks']}")

        # Tile type distribution
        tile_types = {}
        for tf in classroom.room.path.glob("*.json"):
            try:
                with open(tf) as f:
                    t = json.load(f)
                ttype = t.get("type", "unknown")
                tile_types[ttype] = tile_types.get(ttype, 0) + 1
            except Exception:
                pass

        print(f"\n  Tile type distribution:")
        for ttype, count in sorted(tile_types.items()):
            print(f"    {ttype}: {count}")

        # Git history
        print(f"\n  Git history (recent):")
        for entry in classroom.room.history(10):
            print(f"    {entry['hash'][:8]} {entry['message'][:70]}")

        # Show complete agent interaction log
        print(f"\n  📜 Complete interaction log:")
        print(f"  {'='*50}")

        # Teacher tiles
        teacher_tiles = sorted(classroom.room.path.glob("teacher-*.json"))
        student_tiles = sorted(classroom.room.path.glob("student-*.json"))

        all_tiles = []
        for tf in teacher_tiles + student_tiles:
            try:
                with open(tf) as f:
                    t = json.load(f)
                content = t.get("content", {})
                if isinstance(content, dict):
                    all_tiles.append({
                        "file": tf.name,
                        "type": content.get("type", "unknown"),
                        "speaker": content.get("speaker", content.get("student", "?")),
                        "content": content.get("content", "")[:80],
                    })
            except Exception:
                pass

        for tile in all_tiles:
            speaker = tile['speaker']
            ttype = tile['type']
            preview = tile['content']
            emoji = "🎓" if "teacher" in tile['file'] else "✋" if ttype == "question" else "💬"
            print(f"  {emoji} [{speaker}] ({ttype}): {preview}...")

        print(f"\n✅ OpenMAIC Classroom demo complete!")
        print(f"   Room at: {classroom.room.path}")
        print(f"   Total tiles: {status['tiles']}")
        print(f"   Total commits: {len(classroom.room.history(50))}")
        print(f"\n   A ZeroClaw can clone this room and re-experience")
        print(f"   the entire classroom through tile playback.")

    finally:
        print(f"\n  Room preserved at: {tmpdir}")


if __name__ == "__main__":
    demo()

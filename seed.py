"""Seed data per spec §10 — wipe-and-recreate (idempotent by design).

Run order: python seed.py -> python app.py -> localhost:5000.
All students: password 'testpass123', both emails pre-verified, consent set.
Priya (UCSC) has course_visibility='hidden' so the privacy filter is testable.
"""
from app import create_app
from models import db, now_iso
import repository as repo

# (campus, code, title, description) — genuine codes/titles from UC catalogs.
COURSES = [
    # UCSC
    ("UCSC", "CSE 101", "Introduction to Data Structures and Algorithms",
     "Abstract data types, lists, stacks, queues, trees, graphs, sorting and searching, asymptotic analysis."),
    ("UCSC", "CSE 12", "Computer Systems and Assembly Language",
     "Computer organization, machine instructions, assembly language programming, C fundamentals."),
    ("UCSC", "CSE 102", "Introduction to Analysis of Algorithms",
     "Algorithm design techniques: divide and conquer, greedy, dynamic programming; NP-completeness."),
    ("UCSC", "CSE 130", "Principles of Computer Systems Design",
     "Design and implementation of large-scale systems: modularity, naming, concurrency, fault tolerance."),
    ("UCSC", "MATH 19A", "Calculus for Science, Engineering, and Mathematics",
     "Limits, derivatives, applications of differentiation, introduction to integration."),
    ("UCSC", "STAT 131", "Introduction to Probability Theory",
     "Probability spaces, random variables, expectation, discrete and continuous distributions, limit theorems."),
    ("UCSC", "PSYC 1", "Introduction to Psychology",
     "Survey of psychology: perception, learning, memory, cognition, development, social behavior."),
    ("UCSC", "CSE 143", "Introduction to Natural Language Processing",
     "Text processing, language models, syntax, semantics, and applications of NLP."),
    # UCLA
    ("UCLA", "CS 31", "Introduction to Computer Science I",
     "Problem solving and programming in C++: control flow, functions, arrays, classes."),
    ("UCLA", "CS 32", "Introduction to Computer Science II",
     "Object-oriented programming, recursion, linked lists, stacks, queues, trees, algorithm efficiency."),
    ("UCLA", "CS 180", "Introduction to Algorithms and Complexity",
     "Graph algorithms, divide and conquer, greedy methods, dynamic programming, NP-completeness."),
    ("UCLA", "CS 35L", "Software Construction",
     "Practical software construction: shell, scripting, version control, build systems, security basics."),
    ("UCLA", "MATH 31A", "Differential and Integral Calculus",
     "Differential calculus, applications, introduction to integration of functions of one variable."),
    ("UCLA", "STATS 100A", "Introduction to Probability",
     "Probability, random variables, expectation, distributions, law of large numbers, central limit theorem."),
    ("UCLA", "PSYCH 10", "Introductory Psychology",
     "General survey: biological bases of behavior, sensation, learning, memory, personality, social psychology."),
    # UCSD
    ("UCSD", "CSE 12", "Basic Data Structures and Object-Oriented Design",
     "Arrays, linked structures, stacks, queues, trees; object-oriented design in Java."),
    ("UCSD", "CSE 100", "Advanced Data Structures",
     "Balanced trees, hashing, priority queues, graphs, memory management, performance analysis."),
    ("UCSD", "CSE 101", "Design and Analysis of Algorithms",
     "Algorithm design paradigms, graph algorithms, dynamic programming, network flows, NP-completeness."),
    ("UCSD", "MATH 20A", "Calculus for Science and Engineering",
     "Differential calculus of one variable, applications, introduction to the integral."),
    ("UCSD", "MATH 183", "Statistical Methods",
     "Descriptive statistics, probability, estimation, hypothesis testing, regression."),
    ("UCSD", "PSYC 1", "Psychology",
     "Introduction to the science of behavior: cognition, development, personality, mental health."),
    ("UCSD", "CSE 158", "Recommender Systems and Web Mining",
     "Machine learning applied to web data: recommendation, text mining, temporal and social data."),
    # Berkeley
    ("Berkeley", "CS 61A", "Structure and Interpretation of Computer Programs",
     "Abstraction, higher-order functions, recursion, interpreters, programming paradigms in Python."),
    ("Berkeley", "CS 61B", "Data Structures",
     "Fundamental dynamic data structures and their applications; software engineering in Java."),
    ("Berkeley", "CS 170", "Efficient Algorithms and Intractable Problems",
     "Divide and conquer, graph algorithms, dynamic programming, linear programming, NP-completeness."),
    ("Berkeley", "MATH 1A", "Calculus",
     "Limits, continuity, derivatives, applications, definite and indefinite integrals."),
    ("Berkeley", "STAT 134", "Concepts of Probability",
     "Probability, conditional probability, random variables, expectation, distributions, limit laws."),
    ("Berkeley", "PSYCH 1", "General Psychology",
     "Introduction to principal areas, problems, and concepts of psychology."),
    ("Berkeley", "DATA C8", "Foundations of Data Science",
     "Inferential thinking, computational thinking, and real-world data analysis in Python."),
]

# (campus_a, code_a, campus_b, code_b, confidence) — method gemini_flash.
# Anchor pair per spec §10: UCSC CSE 101 <-> UCLA CS 32 at 0.87.
EQUIVALENCIES = [
    ("UCSC", "CSE 101", "UCLA", "CS 32", 0.87),
    ("UCSC", "CSE 101", "Berkeley", "CS 61B", 0.91),
    ("UCSC", "CSE 101", "UCSD", "CSE 100", 0.84),
    ("UCLA", "CS 32", "Berkeley", "CS 61B", 0.88),
    ("UCSC", "CSE 102", "UCLA", "CS 180", 0.90),
    ("UCSC", "CSE 102", "Berkeley", "CS 170", 0.90),
    ("UCSD", "CSE 101", "Berkeley", "CS 170", 0.92),
    ("UCSD", "CSE 101", "UCLA", "CS 180", 0.90),
    ("UCSC", "MATH 19A", "UCLA", "MATH 31A", 0.93),
    ("UCSC", "MATH 19A", "UCSD", "MATH 20A", 0.93),
    ("UCLA", "MATH 31A", "Berkeley", "MATH 1A", 0.90),
    ("UCSD", "MATH 20A", "Berkeley", "MATH 1A", 0.90),
    ("UCSC", "STAT 131", "UCLA", "STATS 100A", 0.89),
    ("UCSC", "STAT 131", "Berkeley", "STAT 134", 0.90),
    ("UCSC", "PSYC 1", "UCLA", "PSYCH 10", 0.94),
    ("UCSC", "PSYC 1", "UCSD", "PSYC 1", 0.95),
    ("UCSD", "PSYC 1", "Berkeley", "PSYCH 1", 0.93),
]

# name, edu_email, personal_email, campus, year, interests, socials,
# visibility, [(campus, code, term), ...]
STUDENTS = [
    ("Maya Chen", "mchen23@ucsc.edu", "maya.chen.codes@gmail.com", "UCSC", "Junior",
     ["algorithms", "film", "climbing"], {"github": "mayachen"},
     "peers", [("UCSC", "CSE 101"), ("UCSC", "CSE 102"), ("UCSC", "MATH 19A")]),
    ("Diego Ramirez", "dramirez@g.ucla.edu", "diego.rmz@outlook.com", "UCLA", "Sophomore",
     ["game dev", "soccer", "music production"], {"instagram": "diego.rmz"},
     "peers", [("UCLA", "CS 32"), ("UCLA", "MATH 31A"), ("UCLA", "PSYCH 10")]),
    ("Sarah Kim", "skim@berkeley.edu", "sarahkim.dev@gmail.com", "Berkeley", "Junior",
     ["systems", "coffee", "open source"], {"github": "sarahk", "twitter": "sarahk_dev"},
     "peers", [("Berkeley", "CS 61B"), ("Berkeley", "CS 170"), ("Berkeley", "STAT 134")]),
    ("Alex Nguyen", "anguyen@ucsd.edu", "alexn.builds@gmail.com", "UCSD", "Senior",
     ["machine learning", "surfing"], {"github": "alexnguyen", "instagram": "alex.builds"},
     "peers", [("UCSD", "CSE 100"), ("UCSD", "CSE 101"), ("UCSD", "CSE 158"), ("UCSD", "MATH 183")]),
    ("Priya Patel", "ppatel@ucsc.edu", "priya.p.writes@gmail.com", "UCSC", "Sophomore",
     ["psychology", "creative writing", "stats"], {"instagram": "priya.writes"},
     "hidden", [("UCSC", "STAT 131"), ("UCSC", "PSYC 1"), ("UCSC", "MATH 19A")]),
    ("Jordan Lee", "jlee@g.ucla.edu", "jordanlee.la@gmail.com", "UCLA", "Junior",
     ["data science", "basketball"], {"twitter": "jlee_la"},
     "peers", [("UCLA", "CS 180"), ("UCLA", "STATS 100A")]),
    ("Emma Wilson", "ewilson@berkeley.edu", "emmawilson.cal@gmail.com", "Berkeley", "Freshman",
     ["psychology", "data science", "hiking"], {"instagram": "emma.cal"},
     "peers", [("Berkeley", "CS 61A"), ("Berkeley", "MATH 1A"), ("Berkeley", "PSYCH 1")]),
]

TERM = "Fall 2026"
PASSWORD = "testpass123"


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        course_index = {}
        for campus, code, title, description in COURSES:
            course_index[(campus, code)] = repo.create_course(campus, code, title, description)

        for campus_a, code_a, campus_b, code_b, confidence in EQUIVALENCIES:
            repo.create_equivalency(
                course_index[(campus_a, code_a)].id,
                course_index[(campus_b, code_b)].id,
                confidence, "gemini_flash",
            )

        student_index = {}
        for (name, edu, personal, campus, year, interests,
             socials, visibility, enrollments) in STUDENTS:
            student = repo.create_student(
                name=name, edu_email=edu, password=PASSWORD, campus=campus,
                year=year, interests=interests, social_handles=socials,
                consent_given_at=now_iso(),
            )
            repo.mark_edu_verified(student.id)
            repo.set_personal_email(student.id, personal)
            repo.mark_personal_verified(student.id)
            if visibility != "peers":
                repo.set_course_visibility(student.id, visibility)
            for campus_c, code_c in enrollments:
                repo.create_enrollment(student.id, course_index[(campus_c, code_c)].id, TERM)
            student_index[name] = student

        # 3 open help requests, one with a response (spec §10).
        maya_req = repo.create_help_request(
            student_index["Maya Chen"].id, course_index[("UCSC", "CSE 101")].id,
            "AVL rotations after delete",
            "I get the single-rotation case, but double rotations after a delete "
            "keep breaking my height invariant. Anyone have a worked example?",
        )
        repo.create_help_response(
            maya_req.id, student_index["Sarah Kim"].id,
            "We covered this in 61B — the trick is re-checking balance factors all "
            "the way up, not just at the deletion point. Happy to walk through it.",
        )
        repo.create_help_request(
            student_index["Diego Ramirez"].id, course_index[("UCLA", "CS 32")].id,
            "Segfault in linked-list destructor",
            "My destructor double-frees when the list has exactly one node. "
            "Valgrind points at the head pointer but it looks fine to me.",
        )
        repo.create_help_request(
            student_index["Jordan Lee"].id, course_index[("UCLA", "STATS 100A")].id,
            "Intuition for the CLT",
            "I can do the problems mechanically but I don't get WHY sample means "
            "go normal. Anyone have a good mental model?",
        )

        print(f"Seeded: {len(COURSES)} courses, {len(EQUIVALENCIES)} equivalencies, "
              f"{len(STUDENTS)} students (all verified, password '{PASSWORD}'), "
              f"3 help requests (1 answered).")
        print("Hidden student for privacy testing: Priya Patel (UCSC).")
        print(f"Try: log in as maya.chen.codes@gmail.com / {PASSWORD}")


if __name__ == "__main__":
    seed()

PLAYBOOK = [
    {
        "title": "Kanban",
        "tag": "Flow",
        "body": "Visualise work, limit work in progress and manage flow. Pull new work only when capacity frees up. Optimise for lead time, not utilisation.",
        "points": ["WIP limits on In Progress and Review", "Explicit policies per column", "Measure lead time and throughput"],
    },
    {
        "title": "Scrum",
        "tag": "Cadence",
        "body": "Time-boxed sprints with a committed scope. The board fills the Sprint Backlog from the top of the ranked backlog until velocity is reached.",
        "points": ["Sprint Planning against velocity", "Daily Scrum around the board", "Review and Retrospective every sprint"],
    },
    {
        "title": "Scrumban",
        "tag": "Hybrid",
        "body": "Scrum roles and rituals with Kanban flow control. A small Ready column acts as a pull buffer, and WIP limits replace sprint commitment.",
        "points": ["Ready buffer with its own limit", "Replenishment on demand", "Continuous flow with regular cadence"],
    },
    {
        "title": "WSJF",
        "tag": "Prioritisation",
        "body": "Weighted Shortest Job First. Each card scores (business value + time urgency + bug uplift) divided by size, so small valuable work rises first.",
        "points": ["Value from priority: critical 13, high 8, medium 5, low 2", "Urgency from the due date", "Divide by story points"],
    },
    {
        "title": "MoSCoW",
        "tag": "Scoping",
        "body": "Every card is classed Must, Should, Could or Won't. Must-haves are protected, Won't items are parked in the backlog explicitly.",
        "points": ["Critical becomes Must", "High with a deadline becomes Must", "Postponed items become Won't"],
    },
    {
        "title": "Story points",
        "tag": "Estimation",
        "body": "Relative sizing on a Fibonacci scale. Estimates come from explicit tags in the notes, otherwise from size keywords and the amount of work described.",
        "points": ["Scale 1, 2, 3, 5, 8, 13", "Spikes capped at 3, bugs at 5", "Anything at 13 should be split"],
    },
    {
        "title": "Definition of Ready",
        "tag": "Checklist",
        "body": "A card enters a sprint or the Ready column only when it is clear enough to start.",
        "points": ["Has a named owner", "Has an outcome that can be verified", "Is estimated and small enough", "Dependencies are known"],
    },
    {
        "title": "Definition of Done",
        "tag": "Checklist",
        "body": "A card moves to Done only when the whole team agrees the work is shippable.",
        "points": ["Reviewed by a second person", "Tested and acceptance criteria met", "Documented where needed", "Deployed or handed over"],
    },
]

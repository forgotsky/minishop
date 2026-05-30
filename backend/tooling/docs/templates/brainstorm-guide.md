# Brainstorming Techniques Guide

This guide provides structured approaches for product discovery and story creation during Devflow initialization and brainstorming sessions.

---

## Technique 1: Guided Discovery (Socratic Method)

Progressive questioning to uncover product vision and features.

### Vision Questions

1. **Problem Space**
   - What problem are you solving?
   - Who experiences this problem most acutely?
   - What happens if this problem isn't solved?

2. **Target Users**
   - Who is your primary user?
   - What's their current workflow/workaround?
   - What frustrates them most about existing solutions?

3. **Success Definition**
   - What does success look like in 6 months?
   - How will you measure success?
   - What's the one thing this product MUST do well?

4. **Competitive Landscape**
   - What alternatives exist today?
   - What's your unfair advantage?
   - Why would users switch to your solution?

### Feature Discovery Questions

1. **Core Value**
   - What's the minimum feature set for first value delivery?
   - If you could only ship one feature, what would it be?
   - What features are table stakes vs. differentiators?

2. **User Journey**
   - What's the first thing a new user should do?
   - What action leads to the "aha moment"?
   - What would make users come back daily?

3. **Constraints**
   - What's technically hardest about this product?
   - What regulatory or compliance constraints exist?
   - What's your deadline or launch constraint?

---

## Technique 2: User Journey Mapping

Walk through user flows to discover features systematically.

### Journey Framework

```
TRIGGER -> ENTRY -> CORE ACTIONS -> SUCCESS -> RETENTION
```

### Journey Questions by Stage

**1. Trigger (What brings users?)**
- How do users discover your product?
- What motivates them to try it?
- What's their emotional state when starting?

**2. Entry (First experience)**
- What's the onboarding flow?
- What information do you need from users?
- How quickly can they see value?

**3. Core Actions (Main usage)**
- What are the 3-5 primary actions users take?
- What workflows are most common?
- What data do they create/consume?

**4. Success (Value delivery)**
- What outcome indicates success for the user?
- How do they know they've achieved their goal?
- What feedback loops exist?

**5. Retention (Coming back)**
- Why would users return?
- What triggers re-engagement?
- How does value compound over time?

### Journey Mapping Exercise

```
For each user type, complete:

User: [Name/Persona]
Goal: [What they want to achieve]

Journey:
1. [Trigger] -> Feature: ___
2. [Entry] -> Feature: ___
3. [Action 1] -> Feature: ___
4. [Action 2] -> Feature: ___
5. [Action 3] -> Feature: ___
6. [Success] -> Feature: ___
7. [Return] -> Feature: ___
```

---

## Technique 3: Rapid Feature List

Fast ideation followed by grouping and prioritization.

### Phase 1: Ideation (5 minutes)

Rules:
- No filtering - capture everything
- Quantity over quality
- Build on others' ideas
- No criticism yet

Prompt questions:
- What features do competitors have?
- What would make users say "wow"?
- What automation would save time?
- What information do users need?
- What actions should be one-click?

### Phase 2: Grouping (3 minutes)

Group features into:
- **User Management** (auth, profiles, settings)
- **Core Features** (primary value proposition)
- **Data & Content** (creation, display, storage)
- **Social/Sharing** (collaboration, communication)
- **Analytics/Insights** (reporting, tracking)
- **Integrations** (third-party connections)
- **Admin/Settings** (configuration, management)

### Phase 3: Prioritization (5 minutes)

Use MoSCoW method:
- **Must Have**: Critical for launch, non-negotiable
- **Should Have**: Important but can work around
- **Could Have**: Nice to have, enhances experience
- **Won't Have**: Out of scope for now

### Rapid List Template

```
MUST HAVE (MVP)
- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3

SHOULD HAVE (v1.1)
- [ ] Feature 4
- [ ] Feature 5

COULD HAVE (Later)
- [ ] Feature 6
- [ ] Feature 7

WON'T HAVE (Not now)
- [ ] Feature 8
```

---

## Technique 4: Story Decomposition

Breaking epics into implementable stories.

### INVEST Criteria

Every story should be:
- **I**ndependent: Can be built separately
- **N**egotiable: Details can be discussed
- **V**aluable: Delivers user value
- **E**stimable: Can be sized
- **S**mall: Fits in a sprint
- **T**estable: Has clear acceptance criteria

### Decomposition Strategies

**1. By User Role**
```
Epic: User Authentication
-> Story: User can sign up with email
-> Story: Admin can invite users
-> Story: User can reset password
```

**2. By Workflow Step**
```
Epic: Checkout Flow
-> Story: User can add items to cart
-> Story: User can enter shipping address
-> Story: User can complete payment
```

**3. By Data Operation (CRUD)**
```
Epic: Task Management
-> Story: User can create a task
-> Story: User can view task list
-> Story: User can edit a task
-> Story: User can delete a task
```

**4. By Happy Path + Edge Cases**
```
Epic: File Upload
-> Story: User can upload single file (happy path)
-> Story: System handles invalid file types
-> Story: System handles upload failures
```

### Story Sizing Reference

| Size | Description | Example |
|------|-------------|---------|
| XS | < 2 hours | Add a button, fix typo |
| S | 2-4 hours | Simple form, basic API endpoint |
| M | 1-2 days | Feature with UI + API + tests |
| L | 3-5 days | Complex feature, multiple components |
| XL | 1+ week | Should be broken down further |

---

## Technique 5: Prioritization Frameworks

### RICE Scoring

```
Score = (Reach x Impact x Confidence) / Effort

Reach: Number of users affected per quarter
Impact: 3=massive, 2=high, 1=medium, 0.5=low, 0.25=minimal
Confidence: 100%, 80%, 50%
Effort: Person-weeks
```

### Impact/Effort Matrix

```
        HIGH IMPACT
             |
   Quick     |    Big Bets
   Wins      |    (schedule these)
   (do first)|
-------------+-------------
   Fill-ins  |    Time Sinks
   (maybe)   |    (avoid)
             |
        LOW IMPACT

      LOW EFFORT  |  HIGH EFFORT
```

### Priority Labels

| Priority | Meaning | Timing |
|----------|---------|--------|
| P0 | Critical | This sprint, drop everything |
| P1 | High | Next sprint |
| P2 | Medium | This quarter |
| P3 | Low | Backlog |

---

## Quick Reference: Init Session (10 min)

1. **Vision** (2 min)
   - What problem are you solving?
   - Who's your primary user?

2. **Core Features** (3 min)
   - What's the one thing this must do well?
   - What are the 3-5 core features?

3. **First Sprint** (3 min)
   - What's your MVP scope?
   - Pick 3-5 stories for sprint 1

4. **Wrap-up** (2 min)
   - Review and confirm
   - Generate story files

---

## Full Workshop Reference (30 min)

1. **Vision Discovery** (5 min)
   - Complete vision questions
   - Define success metrics

2. **User Journey Mapping** (8 min)
   - Map 1-2 primary user journeys
   - Extract features from each step

3. **Rapid Feature List** (7 min)
   - Brainstorm all features
   - Group by category
   - Apply MoSCoW

4. **Story Decomposition** (7 min)
   - Break down Must Have features
   - Apply INVEST criteria
   - Size stories

5. **Sprint Planning** (3 min)
   - Select sprint 1 stories
   - Verify capacity fit
   - Generate files

---
title: Teachers, Students and Fair Rules
kind: book
shelf: how-vefr-works
short: How a big helper teaches a small one, and the rules for what it's fair to learn from.
source: docs/guides/studio-lessons.md
---
Big AI models know a lot, but they need big computers. Small models fit
on a laptop but know less. So the studio tries something clever: a big
model teaches a small one.

* * *

**Teacher and student.** The big model (the *teacher*) answers thousands
of practice questions for one job, like choosing which room a request
belongs in. Checks throw out any answers that break the rules. The small
model (the *student*) practises on the answers that are left. This is
called *distillation*.

* * *

**Test on questions it never saw.** Some questions are kept secret from
the student. After training, it takes those as its exam. If it only did
well on questions it had practised, it memorised; it didn't learn.

* * *

**Fair rules.** Every model and every picture comes with a *licence*: the
rules for using it. Some say "use me for anything". Some say "not for
money". Some say "don't train on my answers". The studio reads the rules
first, and only uses teachers that allow it.

**Public domain** means old work that now belongs to everyone, like
fairy tales from long ago. It's free to learn from.

Reading the rules before you build is part of being a good programmer,
and a good neighbour.

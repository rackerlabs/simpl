# Guidelines for Contributing to `simpl`

`simpl` is a collection of common, recurring patterns we have found useful
while building many REST API's. In @samstav's words, its purpose is: "to
eliminate duplicate code, tests, and documentation, while giving us a
definitive venue for discussion on the more 'generic' modules, utilities, and
even style/contribution/design principles, and standards we [can] use across
projects."

`simpl` is highly opinionated. You won't find generic implementations here. We
stick to certain staples: [bottle](http://bottlepy.org/docs/dev/index.html),
[mongodb](https://www.mongodb.org/), [redis](http://redis.io/),
[git](https://git-scm.com/). Our patterns and modules are unabashedly coupled
to these tools.

While we make every effort to make `simpl` a set of top-notch patterns we are
sure you will find deficiencies. When you do, github
[issues](https://github.com/checkmate/simpl/issues/new) are accepted and
[PR's](https://github.com/checkmate/simpl/pulls) are greatly appreciated.

--------


### The `simpl` vetting process

`simpl` was conceived to solve a particular problem: that of duplicating code
across multiple projects. As we moved from project to project we found certain
patterns were being re-used by copying the code from one project to the next,
which isn't too heinous until you reach about the third or fourth project at
which point one begins to think of better ways to propagate useful patterns.
Our solution was to create the `simpl` package: a place where we can collect
these recurring patterns.

Running with this idea, we have since learned that there are competing demands
introduced by placing these patterns in a semi-official package:

  - Because a pattern is being considered for inclusion in a package that is
  intended to be used across many projects, a more rigorous review process
  seems like a good idea.
  - Identifying a pattern as one we have already implemented most often occurs
  during a mad push to meet a deadline, so the person raising the PR requesting
  the pattern be included in the `simpl` canon needs it merged quickly.

__The following approach aims to reconcile these two competing demands:__

  - The `simpl` package contains two types of modules:
    - __Core__ modules are well-established, curated patterns that have been
    thoroughly vetted. They have earned their place at the root level of the
    `simpl` package. `config`, `exceptions`, `log` are all
    examples of __Core__ modules.
    - The `simpl.incubator` module contains modules that are being considered
    for inclusion in __Core__, but are still being vetted. This solves the
    copy/paste duplication issue while still allowing time for the rigor we
    wish to apply to modules before being accepted into __Core__.
  - Any submitted PR is a candidate for inclusion in __Core__.
  - If a given PR is being contested, the submitter may opt to move the code
  into `simpl.incubator` in an effort to keep the vetting process from blocking
  usage of the code/pattern in other projects.
  - `simpl.incubator` code can eventually be promoted to __Core__. If this
  occurs the module will be moved to the root level of the `simpl` directory
  and will no longer be available in `simpl.incubator`, requiring references to
  the module to be updated when upgrading to the version of `simpl` that has
  the module in __Core__.

--------


### Library Standards

The team has agreed to consistently use several third-party Python packages.
This list will likely be fairly dynamic as we are always looking for things
that will increase our productivity. We have a strong preference for tools that
follow the [Principle of Least Astonishment](http://c2.com/cgi/wiki?PrincipleOfLeastAstonishment)
(also on [Wikipedia](https://en.wikipedia.org/wiki/Principle_of_least_astonishment)).

The list:

  - [bottle](https://pypi.python.org/pypi/bottle): Web application micro-framework
  - [cryptography](https://pypi.python.org/pypi/cryptography): cryptographic recipes and primitives
  - [eventlet](https://pypi.python.org/pypi/eventlet): concurrent networking library
  - [pymongo](https://pypi.python.org/pypi/pymongo): MongoDB driver
  - [redis](https://pypi.python.org/pypi/redis): Redis client library
  - [requests](https://pypi.python.org/pypi/requests): makes http requests virtually painless
  - [tornado](https://pypi.python.org/pypi/tornado): concurrent networking library

--------


### Dealing with optional dependencies

Some of `simpl`'s modules deal with specific tools (like MongoDB or Redis) and
leverage Python packages built for those tools. This presents a problem,
though: what if a project isn't using that particular `simpl` module? We don't
want an unused module to force a project to install a package it has no
intention of using!

The following guidelines aim to solve this issue:
  - When possible, limit package use to the
  [Python Standard Library](https://docs.python.org/3/library/)
  - When other packages are absolutely necessary make sure that the dependency
  remains entirely encapsulated in the module that needs it. This means that
  even though `simpl.bottle` requires the `bottle` package, neither a warning
  or exception should be thrown when importing `simpl.log` or `simpl.git` as
  they can be used just fine without `bottle`.
  - When other packages are optional (e.g. `simpl.middleware.cors` will use
  `webob` but it isn't absolutely required), make sure that the module properly
  handles both cases
  ([cors.py](https://github.com/checkmate/simpl/blob/master/simpl/middleware/cors.py)
  provides a good example of this).

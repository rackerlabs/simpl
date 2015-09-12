# Guidelines for what belongs in `simpl`

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


# Contributing code to Simpl

We'd love to have you use and contribute simpl. Here are the guidelines we'd
like all contributors (including our team at Rackspace) to follow:

 - [Issues and Bugs](#issue)
 - [Feature Requests](#feature)
 - [Submission Guidelines](#submit)
 - [Coding Rules](#rules)
 - [Commit Message Guidelines](#commit)

## <a name="issue"></a> Found an Issue?
If you find a bug in the source code or a mistake in the documentation, you can help us by
submitting an issue to our [GitHub Repository][github]. Even better you can submit a Pull Request
with a fix.

## <a name="feature"></a> Want a Feature?
You can request a new feature by submitting an issue to our [GitHub Repository][github].  If you
would like to implement a new feature then consider what kind of change it is:

* **Major Changes** that you wish to contribute to the project should be discussed first in an issue so that we can better coordinate our efforts, prevent
duplication of work, and help you to craft the change so that it is successfully accepted into the
project.
* **Small Changes** can be crafted and submitted to the [GitHub Repository][github] as a Pull Request.


### Submitting a Pull Request
Before you submit your pull request consider the following guidelines:

* Search [GitHub](https://github.com/checkmate/simpl/pulls) for an open or closed Pull Request
  that relates to your submission. You don't want to duplicate effort.
* Make your changes in a new git branch locally on your development machine:

     ```shell
     git checkout -b my-fix-branch master
     ```

* Create your patch, **including appropriate test cases**.
* Follow our [Coding Rules](#rules).
* Run the full test suite and ensure that all tests pass.
* Commit your changes using a descriptive commit message that follows our
  [commit message conventions](#commit-message-format). Adherence to the [commit message conventions](#commit-message-format)
  is required because release notes are automatically generated from these messages.
  If you have many changes, try to break them up into smaller commits. W try to keep
  commit history clean and useful reference for the hstory of the code.

     ```shell
     git commit -a
     ```
  Note: the optional commit `-a` command line option will automatically "add" and "rm" edited files.

* Build your changes locally to ensure all the tests pass:

    ```shell
    tox
    ```

* Push your branch to your own fork of simpl on GitHub:

    ```shell
    git push myfork my-fix-branch
    ```

* In GitHub, send a pull request to `simpl:master`.
* If changes are suggested then:
  * Make the required updates.
  * Rebase your branch to sync it with any changes in master:

    ```shell
    git rebase master -i
    ```
  * Re-run the test suite to ensure tests are still passing.
  * Rebase your branch and force push to your GitHub repository (this will update your Pull Request):

    ```shell
    git push origin my-fix-branch -f
    ```

That's it! Thank you for your contribution!


#### How Pull Requests are Merged

If you submit a pull request tha you do not wish to be merged, for example if you want to
share a possible implementation or sample code change, then mark it so at the beginning
of the pull request title with an ALL CAPS prefix like `WIP:` or `DO NOT MERGE:`.

Core contributors should:
- not merge any pull request that does not pass automated checks
- not merge a WIP pull request
- not merge their own code (we make exceptions to this rule for when folks are working on holidays or weekends, but not usually in simpl)

#### After your pull request is merged

After your pull request is merged, you can safely delete your branch and pull the changes
from the main (upstream) repository:

* Delete the remote branch on GitHub either through the GitHub web UI or your local shell as follows:

    ```shell
    git push origin --delete my-fix-branch
    ```

* Check out the master branch:

    ```shell
    git checkout master -f
    ```

* Delete the local branch:

    ```shell
    git branch -D my-fix-branch
    ```

* Update your master with the latest upstream version:

    ```shell
    git pull --ff upstream master
    ```

## <a name="rules"></a> Coding Rules
To ensure consistency throughout the source code, keep these rules in mind as you are working:

* All features or bug fixes **must be tested** by one or more tests.
* All modules and methods **must be documented**.
* All code must pass **PEP-8, PEP-257, flake8** checks with any exceptions explicitly noted and justified.
* Follow the OpenStack Hacking Guidelines as documented in [HACKING.rst][hacking] and automated in our style tests using the `hacking` module.
* For simple functions, put tests in the docstring to keep them self-contained.

## <a name="commit"></a> Git Commit Guidelines

We follow AngularJS's very precise rules over how git commit messages can be formatted.  This leads to **more
readable messages** that are easy to follow when looking through the **project history**.  But also,
we use the git commit messages to **generate a change log**.

### Commit Message Format
Each commit message consists of a **header**, a **body** and a **footer**.  The header has a special
format that includes a **type**, a **scope** and a **subject**:

```
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

Any line of the commit message cannot be longer 100 characters! This allows the message to be easier
to read on github as well as in various git tools.

### Type
Must be one of the following:

* **feat**: A new feature
* **fix**: A bug fix
* **docs**: Documentation only changes
* **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing
  semi-colons, etc)
* **refactor**: A code change that neither fixes a bug or adds a feature
* **perf**: A code change that improves performance
* **test**: Adding missing tests
* **chore**: Changes to the build process or auxiliary tools and libraries such as documentation
  generation

### Scope
The scope could be anything specifying place of the commit change. For example `repo`,
`setup`, `deployment`, `component`, `blueprint`, `common`, `contrib`, etc...

### Subject
The subject contains succinct description of the change:

* use the imperative, present tense: "change" not "changed" nor "changes"
* don't capitalize first letter
* no dot (.) at the end

### Body
Just as in the **subject**, use the imperative, present tense: "change" not "changed" nor "changes"
The body should include the motivation for the change and contrast this with previous behavior.

### Footer
The footer should contain any information about **Breaking Changes** and is also the place to
reference GitHub issues that this commit **Closes**.


A detailed explanation can be found in this [document][commit-message-format].

---
Note: inspired by and lifted with gratitude from [AngularJS](http://www.angularjs.org)

[github]: https://github.com/checkmate/simpl
[commit-message-format]: https://docs.google.com/document/d/1QrDFcIiPjSLDn3EL15IJygNPiHORgU1_OOAqWjiDU5Y/edit#
[hacking]: HACKING.rst



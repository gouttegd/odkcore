Ontology Development Kit Core
=============================

This is an _experimental_ project aiming at isolating the core features
of the [Ontology Development
Kit](https://github.com/INCATools/ontology-development-kit) (ODK) and
providing them as a single Python package, independently of the ODK
Docker images.

Rationale
---------
The “Ontology Development Kit” is currently three different things at
once:

* it is a set of executable workflows to manage the lifecycle of an
  ontology;
* it is a tool to create (“seed”, in ODK parlance) and update an
  ontology repository that would use said workflows;
* it is a toolbox of ontology engineering tools, provided as a Docker
  image.

This project posits that the first two things are in fact largely
independent of the third one, and makes the hypothesis that treating
them as such, and clearly separating them as two entities being
developed on their own, could overall facilitate the development of the
entire project.

Therefore, the aim of this “ODK Core” project is to provide the ODK’s
executable workflows and seeding/updating script, independently of the
ODK Docker image. Once it will have reached maturity (if it does!), the
idea is then that the ODK Core will become merely one of the tools
provided by the ODK Docker image.

A secondary goal is to make it possible to seed, update, and use a
ODK-managed repository _without_ using the Docker image at all.

Copying
-------
The ODK Core is free software, published under the same 3-clause BSD
license as the original ODK. See the [LICENSE](LICENSE) file.

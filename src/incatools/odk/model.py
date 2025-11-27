# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dataclasses_json import dataclass_json
from dataclasses_jsonschema import JsonSchemaMixin

# Primitive Types
OntologyHandle = str  ## E.g. uberon, cl; also subset names
Person = str  ## ORCID or github handle
Email = str  ## must be of NAME@DOMAIN form
Url = str


@dataclass_json
@dataclass
class CommandSettings(JsonSchemaMixin):
    """Settings to be provided to a tool like ROBOT."""

    memory_gb: Optional[int] = None
    """Amount of memory in GB to allocate for the command."""


@dataclass_json
@dataclass
class Product(JsonSchemaMixin):
    """The product of an ontology workflow.

    This is the base class for all products, where a product is anything
    that is produced by an ontology workflow. A product can be
    manifested in different formats.

    For example, goslim_prok is a subset (aka slim) product from GO. It
    can be manifested in OBO, OWL, or JSON formats.
    """

    id: str
    """The ontology project identifier (shorthand), e.g. go, obi, envo."""

    description: Optional[str] = None
    """A concise textual description of the product."""

    maintenance: str = "manual"
    """A setting that can be used to change certain assets that are
    typically managed automatically (by the ODK) to manual or other
    maintenance strategies.
    """

    rebuild_if_source_changes: bool = True
    """If false then previously downloaded versions of external
    ontologies are used.
    """

    robot_settings: Optional[CommandSettings] = None
    """Amount of memory to provide for ROBOT when building this product.

    Working with large products such as CHEBI imports may require
    additional memory.
    """


@dataclass_json
@dataclass
class SubsetProduct(Product):
    """Represents an individual subset.

    Examples: goslim_prok (in GO), eco_subset (in RO).
    """

    creators: Optional[List[Person]] = None
    """The people that are credited as creators/maintainers of the subset."""


@dataclass_json
@dataclass
class ComponentProduct(JsonSchemaMixin):
    """Represents an individual component.

    A component is a file that is external to the main -edit file, but
    that contains axioms that should still be considered as belonging
    to this ontology project (contrary to import modules).

    Components are usually maintained externally.
    """

    filename: str
    """The filename of this component."""

    source: Optional[str] = None
    """The URL source from where the component should be obtained."""

    use_template: bool = False
    """If true, the component will be sourced from ROBOT templates."""

    use_mappings: bool = False
    """If true, the component will be sourced from SSSOM mapping sets."""

    template_options: Optional[str] = None
    """ROBOT options passed to the template command.

    Only meaningful if ``use_template`` is set to true."""

    sssom_tool_options: Optional[str] = ""
    """SSSOM-Py options passed to the sssom command.

    Only meaningful if ``use_mappings`` is set to true."""

    templates: Optional[List[str]] = None
    """The ROBOT templates from which the component is derived.

    Only meaningful is ``use_template`` is set to true. The values are
    expected to be the names of template files in the ``src/templates``
    directory. If unset while ``use_template`` is true, the component
    will be assumed to be derived from a template that has the same
    basename as the component itself.
    """

    mappings: Optional[List[str]] = None
    """The SSSOM mapping sets from which the component is derived.

    Only meaningful is ``use_mappings`` is set to true. The values are
    expected to be the names of SSSOM files in the ``src/mappings``
    directory. If unset while ``use_mappings`` is true, the component
    will be assumed to be derived from a SSSOM file that has the same
    basename as the component itself.
    """

    base_iris: Optional[List[str]] = None
    """URI prefixes used to identify terms belonging to the component."""

    make_base: bool = False
    """If true, the remotely fetched component is turned into a base.

    Only meaningful is ``source`` is set.
    """


@dataclass_json
@dataclass
class ImportProduct(Product):
    """Represents an individual import module.

    Example: 'uberon' in GO.

    Import modules are typically built from an upstream source, but this
    can be configured.
    """

    mirror_from: Optional[Url] = None
    """The URL from where to download the source file for this module.

    If unset, the source file will be assumed to be an OBO ontology
    available from ``http://purl.obolibrary.org/obo/...``.
    """

    base_iris: Optional[List[str]] = None
    """URI prefixes used to identify terms belonging to the module."""

    is_large: bool = False
    """Marks the module as being especially large.

    The ODK may take special measures when working with a "large" module
    to reduce the memory footprint of the module.
    """

    module_type: Optional[str] = None
    """The type of the import module.

    This defines how the upstream source will be transformed into the
    actual module. Supported values are: slme, minimal, custom, mirror.
    If unset, the default value is the one set at the level of the
    ImportGroup.
    """

    module_type_slme: Optional[str] = None
    """The method to use for SLME extraction.

    Supported values are: BOT, TOP, STAR. If unset, the default value is
    the one set at the level of the ImportGroup.
    """

    annotation_properties: List[str] = field(
        default_factory=lambda: ["rdfs:label", "IAO:0000115", "OMO:0002000"]
    )
    """The annotation properties to preserve in the import module.

    The default behaviour when producing an import module (unless the
    ``strip_annotation_properties`` setting in ImportGroup is set to
    false) is to strip away all annotation properties except those
    that are explicitly imported and those defined here.
    """

    slme_individuals: Optional[str] = None
    """How to treat individuals when performing SLME extraction.

    See <http://robot.obolibrary.org/extract#syntactic-locality-module-extractor-slme>
    for the list of allowed values and their meaning.
    """

    use_base: bool = False
    """If true, download the -base version of the upstream source.

    Only meaningful if ``mirror_from`` is not set, that is if the
    upstream source is downloaded from http://purl.obolibrary.org/obo/.
    """

    make_base: bool = False
    """If true, the upstream source is turned into a base."""

    use_gzipped: bool = False
    """If true, download the gzipped version of the upstream source.

    Only meaningful if ``mirror_from`` is not set.
    """

    mirror_type: Optional[str] = None
    """How the upstream source is mirrored locally.

    Supported values are: base, custom, no_mirror. Note that ``base`` is
    actually equivalent to setting ``make_base`` to true.
    """


@dataclass_json
@dataclass
class PatternPipelineProduct(Product):
    """Represents an individual pattern pipeline.

    Examples: manual curation pipeline, auto curation pipeline.

    Each pipeline gets its own specific directory.
    """

    dosdp_tools_options: str = "--obo-prefixes=true"
    """Options to pass to the dosdp-tools command."""

    ontology: str = "$(SRC)"
    """The source ontology for the dosdp-tools query command."""


@dataclass_json
@dataclass
class SSSOMMappingSetProduct(Product):
    """Represents a SSSOM mapping set product."""

    mirror_from: Optional[Url] = None
    """The URL from where to download the mapping set."""

    source_file: Optional[str] = None
    """The ontology file from which the mappings should be extracted."""

    sssom_tool_options: Optional[str] = ""
    """SSSOM-Py options passed to `sssom parse` command.

    Only meaningful is ``source_file`` is set and
    ``SSSOMMappingSetGroup.mapping_extractor`` is to set to 'sssom-py'.
    """

    release_mappings: bool = False
    """If true, this mapping set is treated as a release artefact.

    Note that the ``SSSOMMappingSetGroup.release_mappings`` value takes
    precedence if it is set to true.
    """

    source_mappings: Optional[List[str]] = None
    """The mapping sets to merge to create this product.

    The values are expected to be the basenames of other mapping sets
    defined in the SSSOMMappingSetGroup.
    """


@dataclass_json
@dataclass
class BridgeProduct(Product):
    """Represents a bridge ontology generated from mappings."""

    sources: Optional[List[str]] = None
    """The mapping sets from which this bridge is derived.

    The values are expected to be the basenames of SSSOM mapping sets
    defined in the SSSOMMappingSetGroup. If unset, the bridge will be
    generated from a mapping set with the same basename as the bridge
    itself.
    """

    bridge_type: str = "sssom"
    """How the bridge is generated.

    Valid options are 'sssom' for a bridge derived from SSSOM mappings
    (this is the default), or 'custom' for a bridge generated by a
    custom workflow.
    """

    ruleset: str = "default"
    """The SSSOM/T-OWL ruleset to use to derive the bridge.

    The ruleset will be expected to be located in
    ``src/scripts/bridge-XXX.sssomt``, where XXX is the value set here.
    """


@dataclass_json
@dataclass
class BabelonTranslationProduct(Product):
    """Represents a Babelon translation."""

    mirror_babelon_from: Optional[Url] = None
    """If specified this URL is used to mirror the translation."""

    mirror_synonyms_from: Optional[Url] = None
    """If specified this URL is used to mirror the synonym template from."""

    include_robot_template_synonyms: bool = False
    """If true, a ROBOT template synonym table is added in addition to
    the babelon translation table.
    """

    babelon_tool_options: Optional[str] = ""
    """Babelon toolkit options passed to the command used to generate this product."""

    language: str = "en"
    """Language tag (IANA/ISO), e.g 'en', 'fr'."""

    include_not_translated: bool = False
    """If false, NOT_TRANSLATED values are removed during preprocessing."""

    update_translation_status: bool = True
    """If true, translations where the source_value has changed are
    relegated to CANDIDATE status.
    """

    drop_unknown_columns: bool = True
    """If true, columns that are not part of the babelon standard are
    removed during preprocessing.
    """

    auto_translate: bool = False
    """If true, attempt to automatically translate missing values.

    By default, the Babelon toolkit employs LLM-mediated translations
    using the OpenAI API. This may change at anytime.
    """


@dataclass_json
@dataclass
class ProductGroup(JsonSchemaMixin):
    """Represents a product group.

    This is the abstract base class for all product groups. A product
    group is a simple holder for a list of products, with the ability to
    set configurations that hold by default for all products within that
    group.
    """

    disabled: bool = False
    """If true, this entire group is not used.

    FIXME: This has currently no effect at all.
    """

    rebuild_if_source_changes: bool = True
    """If false then upstream ontology is re-downloaded any time the
    -edit file changes.

    FIXME: This has currently no effect at all.
    """

    def derive_fields(self, project: OntologyProject) -> None:
        """Derive field values wherever needed.

        This method may be overriden by any product group subclass that
        needs to automatically set some values (either in the group
        itself, or in any of its product). Notably, this can be used to
        propagate default values set at the level of the group down to
        the individual products.
        """
        pass


@dataclass_json
@dataclass
class SubsetGroup(ProductGroup):
    """The configuration section for all the subset products.

    This controls the export of subsets/slims into the ``subsets/``
    directory.
    """

    products: List[SubsetProduct] = field(default_factory=lambda: [])
    """All the subset products."""


@dataclass_json
@dataclass
class ImportGroup(ProductGroup):
    """The configuration section for all the import modules.

    This controls the extraction of import modules into the ``imports/``
    directory.
    """

    products: List[ImportProduct] = field(default_factory=lambda: [])
    """All the import modules used by the project."""

    module_type: str = "slme"
    """The default type of import module.

    This value is used for any import module that does not define its
    own type. Support values are: slme, minimal, custom.
    """

    module_type_slme: str = "BOT"
    """The default extraction method for SLME import modules.

    This value is used for any SLME import module that does not define
    its own method. Supported values are: BOT, TOP, STAR.
    """

    slme_individuals: str = "include"
    """Default individuals option.

    This value is used for any SLME import module that does not define
    its own policy about individuals. See
    <http://robot.obolibrary.org/extract#syntactic-locality-module-extractor-slme>
    for supported values and their meaning.
    """

    mirror_retry_download: int = 4
    """How many times to try downloading the source of an import module.

    This corresponds to the cURL --retry parameter,
    see <http://www.ipgp.fr/~arnaudl/NanoCD/software/win32/curl/docs/curl.html>.
    """

    mirror_max_time_download: int = 200
    """How long downloading the source of an import module is allowed to take.

    This corresponds to the cURL --max-time parameter (in seconds), see
    <http://www.ipgp.fr/~arnaudl/NanoCD/software/win32/curl/docs/curl.html>.
    """

    release_imports: bool = False
    """If true, imports are copied to the release directory."""

    use_base_merging: bool = False
    """If true, merge all mirrors before determining a suitable seed.

    Beware that base merging can be a quite costly process.
    """

    base_merge_drop_equivalent_class_axioms: bool = False
    """If true, remove EquivalentClasses axioms prior to extraction.

    Only meaningful if ``use_base_merging`` is set to true. Do not
    activate this feature unless you are positive that your base merging
    process only leverages true base files, with asserted SubClassOf
    axioms.
    """

    exclude_iri_patterns: Optional[List[str]] = None
    """IRI patterns of entities to remove from the merged import module.

    Only meaningful if ``use_base_merging`` is set to true.
    """

    export_obo: bool = False
    """If true, write import modules in OBO format in addition to OWL format."""

    annotation_properties: List[str] = field(
        default_factory=lambda: ["rdfs:label", "IAO:0000115", "OMO:0002000"]
    )
    """The default list of annotation properties to preserve.

    Only meaningful is ``strip_annotation_properties`` is set to true
    (which is the case by default).
    """

    strip_annotation_properties: bool = True
    """If true, strip away annotation properties from the import modules.

    Annotation properties that are explicitly imported or that are
    listed in ``annotation_properties`` (either at the ImportGroup level
    or at the level of an individual module) will be preserved.
    """

    annotate_defined_by: bool = False
    """If true, annotate each import class with rdfs:definedBy.

    If base merging is enabled, the annotation will be added directly to
    the merged import module. Otherwise, it will be added during the
    release process to the full release artefact.
    """

    scan_signature: bool = True
    """If true, the edit file is scanned for additional terms to import.

    Otherwise, imports are seeded solely from the manually maintained
    ``*_terms.txt`` files. Note that setting this option to false makes
    Protégé-based declarations of terms to import impossible.
    """

    def derive_fields(self, project: OntologyProject) -> None:
        self.special_products = []
        for p in self.products:
            if p.module_type is None:
                # Use group-level module type
                p.module_type = self.module_type
            elif p.module_type == "fast_slme":
                # Accept fast_slme as a synonym for slme, for backwards
                # compatibility
                p.module_type = "slme"
            if p.module_type == "slme":
                # Use group-level SLME parameters unless overriden
                if p.module_type_slme is None:
                    p.module_type_slme = self.module_type_slme
                if p.slme_individuals is None:
                    p.slme_individuals = self.slme_individuals
            if p.base_iris is None:
                p.base_iris = ["http://purl.obolibrary.org/obo/" + p.id.upper()]
            if (
                p.is_large
                or p.module_type != self.module_type
                or (
                    p.module_type == "slme"
                    and (
                        p.module_type_slme != self.module_type_slme
                        or p.slme_individuals != self.slme_individuals
                    )
                )
            ):
                # This module will require a distinct rule
                self.special_products.append(p)


@dataclass_json
@dataclass
class ReportConfig(JsonSchemaMixin):
    """The configuration section for ROBOT reports."""

    fail_on: Optional[str] = None
    """The error level that should trigger a failure.

    See <http://robot.obolibrary.org/report#failing> for details.
    """

    use_labels: bool = True
    """If true, generated reports will include entities' labels."""

    use_base_iris: bool = True
    """If true, only reports on problems with entities belonging to this ontology.

    Whether a given entity belongs to this ontology or not is determined
    using the ``OntologyProject.namespaces`` property.
    """

    custom_profile: bool = False
    """If true, use a custom ROBOT profile instead of the built-in profile."""

    report_on: List[str] = field(default_factory=lambda: ["edit"])
    """The ontology file on which the report command should be run.

    This can either be the keyword `edit` to indicate the edit file, or
    the full name of any ontology file.
    """

    ensure_owl2dl_profile: bool = True
    """Checks that the main release artefact conforms to the OWL2 DL profile."""

    release_reports: bool = False
    """If true, release reports are added as assets to the release.

    Reports will be copied over to the top-level ``reports/`` directory.
    """

    custom_sparql_checks: Optional[List[str]] = field(
        default_factory=lambda: [
            "owldef-self-reference",
            "iri-range",
            "label-with-iri",
            "multiple-replaced_by",
            "dc-properties",
        ]
    )
    """Additional SPARQL checks to run.

    For each NAME provided here, the file containing the related SPARQL
    query must be available in ``src/sparql/NAME-violation.sparql``.

    The following custom SPARQL checks are available:
    - owldef-self-reference
    - redundant-subClassOf
    - taxon-range
    - iri-range
    - iri-range-advanced
    - label-with-iri
    - multiple-replaced_by
    - term-tracker-uri
    - illegal-date
    - dc-properties
    """

    custom_sparql_exports: Optional[List[str]] = field(
        default_factory=lambda: [
            "basic-report",
            "class-count-by-prefix",
            "edges",
            "xrefs",
            "obsoletes",
            "synonyms",
        ]
    )
    """Custom reports to generate.

    For each NAME provided here, the file containing the related SPARQL
    query must be available in ``src/sparql/NAME.sparql``.
    """

    sparql_test_on: List[str] = field(default_factory=lambda: ["edit"])
    """The ontology file on which to run the custom SPARQL checks.

    This can either be the keyword `edit` to indicate the edit file, or
    the full name of any ontology file.
    """

    upper_ontology: Optional[str] = None
    """IRI of an upper ontology to check the current ontology against."""


@dataclass_json
@dataclass
class DocumentationGroup(JsonSchemaMixin):
    """Configuration section for the repos documentation system."""

    documentation_system: Optional[str] = "mkdocs"
    """The documentation generation system to use.

    Currently, only 'mkdocs' is supported.
    """


@dataclass_json
@dataclass
class ComponentGroup(ProductGroup):
    """The configuration section for the components."""

    products: List[ComponentProduct] = field(default_factory=lambda: [])
    """All the components used in this ontology."""

    def derive_fields(self, project: OntologyProject) -> None:
        for product in self.products:
            if product.base_iris is None:
                product.base_iris = [project.uribase + "/" + project.id.upper()]
            if product.use_template and product.templates is None:
                product.templates = [product.filename.split(".")[0] + ".tsv"]
            elif product.use_mappings and product.mappings is None:
                product.mappings = [product.filename.split(".")[0] + ".sssom.tsv"]


@dataclass_json
@dataclass
class PatternPipelineGroup(ProductGroup):
    """The configuration for the DOSDP pattern pipelines.

    This controls the handling of patterns data in the
    ``src/patterns/data/`` directory.
    """

    products: List[PatternPipelineProduct] = field(default_factory=lambda: [])
    """All the pattern pipelines used in this ontology."""

    matches: Optional[List[PatternPipelineProduct]] = None
    """The pipelines specifically configured for matching, NOT generating."""


@dataclass_json
@dataclass
class SSSOMMappingSetGroup(JsonSchemaMixin):
    """Configuration section for the SSSOM mapping set products.

    This controls the production of the SSSOM files in the
    ``src/mappings/`` directory.
    """

    release_mappings: bool = False
    """If true, mappings are copied to the release directory."""

    mapping_extractor: str = "sssom-py"
    """The tool to use to extract mappings from an ontology.

    Only meaningful for mapping sets whose ``maintenance`` property is
    set to 'extract'. Possible values: sssom-py, sssom-java.
    """

    products: List[SSSOMMappingSetProduct] = field(default_factory=lambda: [])
    """All the mapping sets defined in this project."""

    def derive_fields(self, project: OntologyProject) -> None:
        if self.release_mappings:  # All sets are released
            released_products = [p for p in self.products]
        else:  # Only some selected sets are released
            released_products = [p for p in self.products if p.release_mappings]
        if len(released_products) > 0:
            self.released_products = released_products

        for product in self.products:
            if product.maintenance == "merged":
                if product.source_mappings is None:
                    # Merge all other non-merge sets to make this one
                    product.source_mappings = [
                        p.id for p in self.products if p.maintenance != "merged"
                    ]
                else:
                    # Check that all listed source sets exist
                    for source in product.source_mappings:
                        if source not in [p.id for p in self.products]:
                            raise Exception(f"Unknown source mapping set '{source}'")
            elif product.maintenance == "extract":
                if product.source_file is None:
                    product.source_file = "$(EDIT_PREPROCESSED)"


@dataclass_json
@dataclass
class BridgeGroup(ProductGroup):
    """The configuration section for the bridge ontologies.

    This controls the production of the bridge ontology files in the
    ``src/ontology/bridges/`` directory.
    """

    products: List[BridgeProduct] = field(default_factory=lambda: [])
    """All the bridges defined in this project."""

    def derive_fields(self, project: OntologyProject) -> None:
        for product in [p for p in self.products if p.bridge_type == "sssom"]:
            if project.sssom_mappingset_group is None:
                raise Exception(
                    "The project defines a SSSOM-derived bridge but has no SSSOM group"
                )

            if product.sources is None:
                # Default source is a mapping set with the same name as
                # the bridge itself
                product.sources = [product.id]

            for source in product.sources:
                if source not in [
                    p.id for p in project.sssom_mappingset_group.products
                ]:
                    raise Exception(
                        f"Missing source SSSOM set '{source}' for bridge '{product.id}'"
                    )


@dataclass_json
@dataclass
class BabelonTranslationSetGroup(JsonSchemaMixin):
    """The configuration section for the Babelon translations."""

    release_merged_translations: bool = False
    """If true, release all translations as a single TSV and a single JSON file."""

    predicates: Optional[List[str]] = field(
        default_factory=lambda: ["IAO:0000115", "rdfs:label"]
    )
    """The list of predicates that are considered during translation preparation."""

    oak_adapter: str = "pronto:$(ONT).obo"
    """The OAK adapter to use to process the translation tables.

    The path part of the selector should match the
    ``translate_ontology`` property.
    """

    translate_ontology: str = "$(ONT).obo"
    """The name of the ontology that should be translated.

    This should match the path part of the selector set in the
    ``oak_adapter`` property.
    """

    products: Optional[List[BabelonTranslationProduct]] = None
    """All translation products in this ontology."""


@dataclass_json
@dataclass
class RobotPlugin(JsonSchemaMixin):
    """Represents a ROBOT plugin required by this ontology."""

    name: str = ""
    """The Basename for the plugin."""

    mirror_from: Optional[str] = None
    """The URL from where the plugin should be downloaded."""


@dataclass_json
@dataclass
class RobotOptionsGroup(JsonSchemaMixin):
    """The configuration section for additional ROBOT-specific options."""

    reasoner: str = "ELK"
    """The reasoner to use in ROBOT commands that need one."""

    obo_format_options: str = ""
    """Additional options for ``robot convert`` when exporting to OBO.

    Default is ``--clean-obo "strict drop-untranslatable-axioms"``.
    """

    relax_options: str = "--include-subclass-of true"
    """Additional options to pass to ``robot relax``."""

    reduce_options: str = "--include-subproperties true"
    """Additional options to pass to ``robot reduce``."""

    plugins: Optional[List[RobotPlugin]] = None
    """List of ROBOT plugins used by this project."""

    report: Dict[str, Any] = field(default_factory=lambda: ReportConfig().to_dict())
    """Settings for ROBOT report, ROBOT verify and additional reports that are generated."""


@dataclass_json
@dataclass
class OntologyProject(JsonSchemaMixin):
    """The top-level configuration for an ontology project/repository.

    This is divided into project-wide settings, plus groups of products.
    """

    id: OntologyHandle = ""
    """The OBO identifier for this ontology.

    The identifier must be in lowercase.

    Examples: uberon, go, cl, envo, chebi.
    """

    config_hash: Optional[str] = None
    """Configuration hash.

    This will be automatically generated and must not be set by the
    user. This is intended to allow checking whether the configuration
    of the project has changed since the standard Makefile was last
    generated.
    """

    title: str = ""
    """Concise descriptive text about this ontology."""

    git_user: str = ""
    """The user name for ``git``.

    This is necessary for generating releases.
    """

    repo: str = "noname"
    """The name of the repo.

    This should not include the name of the organisation. For example,
    'cell-ontology', NOT 'obophenotype/cell-ontology'.
    """

    repo_url: str = ""
    """URL of the online repository.

    If set, this must point to a browsable version of the repository root.
    """

    github_org: str = ""
    """Name of the Github user or organisation that will host the repo.

    Examples: obophenotype, cmungall.
    """

    git_main_branch: str = "main"
    """The name of the main branch of the repository."""

    edit_format: str = "owl"
    """The format of the edit file.

    Allowed values are ``obo`` or ``owl``. Note that ``owl`` here means
    OWL Functional Syntax.
    """

    run_as_root: bool = False
    """Run all commands under the identity of the super-user.

    Use this if you have custom workflows that require admin rights
    (e.g. to install Debian packages not provided by the ODK).
    """

    robot_version: Optional[str] = None
    """Only set this if you want to pin to a specific robot version.

    FIXME: This has currently no effect. The ROBOT version used will
    always be the one provided by the ODK, which is typically the latest
    available version at the time the ODK is released.
    """

    robot_settings: Optional[CommandSettings] = None
    """Settings to pass to ROBOT.

    FIXME: This has currently no effect.
    """

    robot_java_args: Optional[str] = ""
    """Java args to pass to ROBOT at runtime, such as -Xmx6G."""

    owltools_memory: Optional[str] = ""
    """Amount of memory to allocate to OWLTools.

    Note that OWLTools is no longer used by any standard ODK workflow,
    but the option may still impact any remaning use of OWLTools in a
    custom workflow.
    """

    use_external_date: bool = False
    """Use the host ``date`` command to infer the current date.

    The default behaviour is to use the ``date`` command from within the
    Docker container.
    """

    remove_owl_nothing: bool = False
    """Remove owl:Nothing from all release artefacts."""

    export_project_yaml: bool = False
    """Generate a complete configuration file.

    If set to true, when seeding the repository an additional
    ``project.yaml`` file will be generated, containing the complete
    configuration for the repository (including default option values).
    """

    exclude_tautologies: str = "structural"
    """Remove tautologies from release artefacts.

    Use this option to remove tautologies such as A SubClassOf: owl:Thing
    or owl:Nothing SubClassOf: A. For more information see
    <http://robot.obolibrary.org/reason#excluding-tautologies>.
    """

    primary_release: str = "full"
    """The release artefact to publish as the primary release artefact.

    This can be any of the supported release artefact type, e.g. 'full',
    'base', 'simple', etc.
    """

    license: str = "https://creativecommons.org/licenses/unspecified"
    """The license under whose terms the ontology is supplied.

    This should be a resolvable IRI and will by default appear as an
    annotation in the seeded ontology.
    """

    description: str = "None"
    """A short description of the ontology."""

    use_dosdps: bool = False
    """Enables the use of DOSDP patterns."""

    use_templates: bool = False
    """Enables the use of ROBOT templates."""

    use_mappings: bool = False
    """Enables the use of SSSOM mapping sets."""

    use_translations: bool = False
    """Enables the use of Babelon for multilingual support."""

    use_env_file_docker: bool = False
    """Uses a file to pass environment variables to the Docker container."""

    use_custom_import_module: bool = False
    """Enables the use of a custom import module.

    If true, this adds a custom import module which is managed through a
    ROBOT template. This can also be used to manage your module seed.
    """

    manage_import_declarations: bool = True
    """Lets the ODK manage import declarations.

    If true, import declarations in the edit file and redirections in
    the XML catalog will be entirely managed by the ODK.
    """

    custom_makefile_header: str = """
# ----------------------------------------
# More information: https://github.com/INCATools/ontology-development-kit/
"""
    """A multiline string that is added to the Makefile."""

    use_context: bool = False
    """Uses a context file to manage prefixes used across the project."""

    public_release: str = "none"
    """If true add targets to run automated releases.

    This is experimental. Current options: github_curl, github_python.
    """

    public_release_assets: Optional[List[str]] = None
    """Files to deploy as release assets.

    If unset, the standard ODK assets will be deployed.
    """

    release_date: bool = False
    """Tags releases with a oboInOwl:date annotation."""

    allow_equivalents: str = "asserted-only"
    """Allows EquivalentClasses axioms between named classes.

    See <http://robot.obolibrary.org/reason#equivalent-class-axioms>
    for details.
    """

    ci: Optional[List[str]] = field(default_factory=lambda: ["github_actions"])
    """The service to use to run continuous integration checks.

    Possible values: travis, github_actions, gitlab-ci.
    """

    workflows: Optional[List[str]] = field(default_factory=lambda: ["docs", "qc"])
    """Workflows that are synced when the repo is updated.

    Currently available workflows: docs, diff, qc, release-diff.
    """

    import_pattern_ontology: bool = False
    """Imports the DOSDP-derived pattern.owl file into the ontology."""

    import_component_format: str = "ofn"
    """The default serialisation for all components and imports."""

    create_obo_metadata: bool = True
    """Generates metadata files for the OBO Foundry."""

    gzip_main: bool = False
    """Produces gzipped versions of the main artefacts in all formats."""

    release_artefacts: List[str] = field(default_factory=lambda: ["full", "base"])
    """The types of release artefacts to produce.

    Supported values: base, full, baselite, simple, non-classified,
    simple-non-classified, basic.
    """

    release_use_reasoner: bool = True
    """Uses the reasoner during the release process.

    If enabled, the reasoner will be used for three operations: reason
    (the computation of the SubClassOf hierarchy), materialize (the
    materialisation of simple existential/object property restrictions),
    and reduce (the removal of redundant SubClassOf axioms).
    """

    release_annotate_inferred_axioms: bool = False
    """Annotates inferred axioms as such."""

    release_materialize_object_properties: Optional[List[str]] = None
    """The object properties to materialise at release time."""

    export_formats: List[str] = field(default_factory=lambda: ["owl", "obo"])
    """The formats the release artefacts should be exported to.

    Allowed values: owl, obo, json, ttl, db.

    Note that here, ``owl`` means RDF/XML, ``json`` means OBOGraph-Json,
    and ``db`` means SemSQL.
    """

    namespaces: Optional[List[str]] = None
    """The namespaces that are considered at home in this ontology.

    This is used by certain filter commands to exclude entities that are
    considered "foreign" to the ontology.
    """

    use_edit_file_imports: bool = True
    """Uses the edit file to determine which imports are included.

    If enabled, the ODK will release the ontology with the imports
    explicitly specified by owl:imports declarations in the edit file.
    Otherwise, the ODK will build and release the ontology with all the
    import modules and components specified in the ODK configuration,
    regardless of any owl:imports declaration.
    """

    dosdp_tools_options: str = "--obo-prefixes=true"
    """Default parameters for dosdp-tools."""

    travis_emails: Optional[List[Email]] = None  ## ['obo-ci-reports-all@groups.io']
    """Emails to use in travis configurations."""

    catalog_file: str = "catalog-v001.xml"
    """Name of the catalog file to be used by the build."""

    uribase: str = "http://purl.obolibrary.org/obo"
    """Base URI for PURLs.

    For an example see
    <https://gitlab.c-path.org/c-pathontology/critical-path-ontology>.
    """

    uribase_suffix: Optional[str] = None
    """Suffix for the URI base.

    If not set, the suffix will be the ontology identifier by default.
    """

    contact: Optional[Person] = None
    """Single contact person for this ontology, as required by OBO."""

    creators: Optional[List[Person]] = None
    """List of ontology creators (currently setting this has no effect)."""

    contributors: Optional[List[Person]] = None
    """List of ontology contributors (currently setting this has no effect)."""

    ensure_valid_rdfxml: bool = True
    """When enabled, ensures that any RDF/XML product file is valid."""

    extra_rdfxml_checks: bool = False
    """Performs even more checks on RDF/XML product files."""

    release_diff: bool = False
    """Generates a diff with the previous release."""

    robot: RobotOptionsGroup = field(default_factory=lambda: RobotOptionsGroup())
    """ROBOT-related options."""

    # product groups
    import_group: Optional[ImportGroup] = None
    """Configuration section for import modules."""

    components: Optional[ComponentGroup] = None
    """Configuration section for components."""

    documentation: Optional[DocumentationGroup] = None
    """Configuration section for documentation-related options."""

    subset_group: Optional[SubsetGroup] = None
    """Configuration section for subset products."""

    pattern_pipelines_group: Optional[PatternPipelineGroup] = None
    """Configuration section for DOSDP pipelines."""

    sssom_mappingset_group: Optional[SSSOMMappingSetGroup] = None
    """Configuration section for SSSOM mapping sets."""

    bridge_group: Optional[BridgeGroup] = None
    """Configuration section for bridge ontology products."""

    babelon_translation_group: Optional[BabelonTranslationSetGroup] = None
    """Configuration section for Babelon translations."""

    def derive_fields(self) -> None:
        """Derives default values whenever needed."""
        if self.import_group is not None:
            self.import_group.derive_fields(self)
        if self.subset_group is not None:
            self.subset_group.derive_fields(self)
        if self.pattern_pipelines_group is not None:
            self.pattern_pipelines_group.derive_fields(self)
        if self.sssom_mappingset_group is not None:
            self.sssom_mappingset_group.derive_fields(self)
        if self.bridge_group is not None:
            self.bridge_group.derive_fields(self)
        if self.components is not None:
            self.components.derive_fields(self)

        if "--clean-obo" not in self.robot.obo_format_options:
            if len(self.robot.obo_format_options) > 0:
                self.robot.obo_format_options += " "
            self.robot.obo_format_options += (
                '--clean-obo "strict drop-untranslatable-axioms"'
            )

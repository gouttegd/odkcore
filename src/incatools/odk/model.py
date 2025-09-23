# odkcore - Ontology Development Kit Core
# Copyright © 2025 ODK Developers
#
# This file is part of the ODK Core project and distributed under the
# terms of a 3-clause BSD license. See the LICENSE file in that project
# for the detailed conditions.

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
    """
    Settings to be provided to a tool like ROBOT
    """

    memory_gb: Optional[int] = None
    """Amount of memory in GB to provide for tool such as robot"""


@dataclass_json
@dataclass
class Product(JsonSchemaMixin):
    """
    abstract base class for all products.

    Here, a product is something that is produced by an ontology workflow.
    A product can be manifested in different formats.

    For example, goslim_prok is a subset (aka slim) product from GO,
    this can be manifest as obo, owl, json
    """

    id: str
    """ontology project identifier / shorthand; e.g. go, obi, envo"""

    description: Optional[str] = None
    """A concise textual description of the product"""

    maintenance: str = "manual"
    """A setting that can be used to change certain assets that are typically managed automatically (by ODK) to manual or other maintenance strategies."""

    rebuild_if_source_changes: bool = True
    """If false then previously downloaded versions of external ontologies are used"""

    robot_settings: Optional[CommandSettings] = None
    """Amount of memory to provide for robot. Working with large products such as CHEBI imports may require additional memory"""


@dataclass_json
@dataclass
class SubsetProduct(Product):
    """
    Represents an individual subset.
    Examples: goslim_prok (in go), eco_subset (in ro)
    """

    creators: Optional[List[Person]] = None
    """list of people that are credited as creators/maintainers of the subset"""


@dataclass_json
@dataclass
class ComponentProduct(JsonSchemaMixin):
    """
    Represents an individual component
    Examples: a file external to the edit file that contains axioms that belong to this ontology
    Components are usually maintained manually.
    """

    filename: Optional[str] = None
    """The filename of this component"""

    source: Optional[str] = None
    """The URL source for which the component should be obtained."""

    use_template: bool = False
    """If true, the component will be sourced by a template"""

    use_mappings: bool = False
    """If true, the component will be sourced from one or more SSSOM mapping files"""

    template_options: Optional[str] = None
    """ROBOT options passed to the template command"""

    sssom_tool_options: Optional[str] = ""
    """SSSOM toolkit options passed to the sssom command used to generate this product command"""

    templates: Optional[List[str]] = None
    """A list of ROBOT template names. If set, these will be used to source this component."""

    mappings: Optional[List[str]] = None
    """A list of SSSOM template names. If set, these will be used to source this component."""

    base_iris: Optional[List[str]] = None
    """A list of URI prefixes used to identify terms belonging to the component."""

    make_base: bool = False
    """if make_base is true, the file is turned into a base (works with `source`)."""


@dataclass_json
@dataclass
class ImportProduct(Product):
    """
    Represents an individual import
    Examples: 'uberon' (in go)
    Imports are typically built from an upstream source, but this can be configured
    """

    mirror_from: Optional[Url] = None
    """if specified this URL is used rather than the default OBO PURL for the main OWL product"""

    base_iris: Optional[List[str]] = None
    """if specified this URL is used rather than the default OBO PURL for the main OWL product"""

    is_large: bool = False
    """if large, ODK may take measures to reduce the memory footprint of the import."""

    module_type: Optional[str] = None
    """Module type. Supported: slme, minimal, custom, mirror"""

    module_type_slme: Optional[str] = None
    """SLME module type. Supported: BOT, TOP, STAR"""

    annotation_properties: List[str] = field(
        default_factory=lambda: ["rdfs:label", "IAO:0000115", "OMO:0002000"]
    )
    """Define which annotation properties to pull in."""

    slme_individuals: Optional[str] = None
    """See http://robot.obolibrary.org/extract#syntactic-locality-module-extractor-slme"""

    use_base: bool = False
    """if use_base is true, try use the base IRI instead of normal one to mirror from."""

    make_base: bool = False
    """if make_base is true, try to extract a base file from the mirror."""

    use_gzipped: bool = False
    """if use_gzipped is true, try use the base IRI instead of normal one to mirror from."""

    mirror_type: Optional[str] = None
    """Define the type of the mirror for your import. Supported: base, custom, no_mirror."""


@dataclass_json
@dataclass
class PatternPipelineProduct(Product):
    """
    Represents an individual pattern pipeline
    Examples: manual curation pipeline, auto curation pipeline
    Each pipeline gets their own specific directory
    """

    dosdp_tools_options: str = "--obo-prefixes=true"
    ontology: str = "$(SRC)"


@dataclass_json
@dataclass
class SSSOMMappingSetProduct(Product):
    """
    Represents an SSSOM Mapping template template
    """

    mirror_from: Optional[Url] = None
    """if specified this URL is used to mirror the mapping set."""

    source_file: Optional[str] = None
    """The name of the file from which the mappings should be extracted"""

    sssom_tool_options: Optional[str] = ""
    """SSSOM toolkit options passed to the sssom command used to generate this product command"""

    release_mappings: bool = False
    """If set to True, this mapping set is treated as an artifact to be released."""

    source_mappings: Optional[List[str]] = None
    """The mapping sets to merge to create this product."""


@dataclass_json
@dataclass
class BridgeProduct(Product):
    """
    Represents a bridge ontology generated from mappings
    """

    sources: Optional[List[str]] = None
    """The mapping sets from which this bridge is derived. If unset, the bridge will be generated from a mapping set with the same basename."""

    bridge_type: str = "sssom"
    """How the bridge is generated. Valid options are "sssom" for a bridge derived from SSSOM mappings, or "custom" for a bridge generated by a custom workflow."""

    ruleset: str = "default"
    """The SSSOM/T-OWL ruleset to use to derive the bridge."""


@dataclass_json
@dataclass
class BabelonTranslationProduct(Product):
    """
    Represents a Babelon Translation
    """

    mirror_babelon_from: Optional[Url] = None
    """if specified this URL is used to mirror the translation."""

    mirror_synonyms_from: Optional[Url] = None
    """if specified this URL is used to mirror the synonym template from."""

    include_robot_template_synonyms: bool = False
    """if include_robot_template_synonyms is true, a ROBOT template synonym table is added in addition to the babelon translation table."""

    babelon_tool_options: Optional[str] = ""
    """Babelon toolkit options passed to the command used to generate this product command"""

    language: str = "en"
    """Language tag (IANA/ISO), e.g 'en', 'fr'."""

    include_not_translated: bool = False
    """if include_not_translated is 'false' NOT_TRANSLATED values are removed during preprocessing."""

    update_translation_status: bool = True
    """if update_translation_status is 'true', translations where the source_value has changed are relegated to CANDIDATE status."""

    drop_unknown_columns: bool = True
    """if drop_unknown_columns is 'true' columns that are not part of the babelon standard are removed during preprocessing."""

    auto_translate: bool = False
    """if auto_translate is true, missing values are being translated using the babelon toolkit during preprocessing. By default, the toolkit employs LLM-mediated translations using the OpenAI API. This default may change at any time."""


@dataclass_json
@dataclass
class ExportProduct(Product):
    """
    Represents a export product, such as one produced by a SPARQL query
    """

    method: str = "sparql"
    """How the export is generated. Currently only SPARQL is supported"""

    output_format: str = "tsv"
    """Output format, see robot query for details."""

    is_validation_check: bool = False
    """If true, then the presence of one or more results in query results in pipeline fail. Note these are in addition to the main robot report command"""

    export_specification: Optional[str] = None
    """Specification such as a SPARQL query. If unset, assumes a default path of ../sparql/{{id}}.sparql"""


@dataclass_json
@dataclass
class ProductGroup(JsonSchemaMixin):
    """
    abstract base class for all product groups.

    A product group is a simple holder for a list of
    groups, with the ability to set configurations that
    hold by default for all within that group.
    """

    disabled: bool = False
    """if set then this is not used"""

    rebuild_if_source_changes: bool = True
    """if false then upstream ontology is re-downloaded any time edit file changes"""

    def derive_fields(self, project):
        pass


@dataclass_json
@dataclass
class SubsetGroup(ProductGroup):
    """
    A configuration section that consists of a list of `SubsetProduct` descriptions

    Controls export of subsets/slims into the "subsets/" directory
    """

    products: List[SubsetProduct] = field(default_factory=lambda: [])
    """all subset products"""


@dataclass_json
@dataclass
class ImportGroup(ProductGroup):
    """
    A configuration section that consists of a list of `ImportProduct` descriptions

    Controls extraction of import modules via robot extract into the "imports/" directory
    """

    products: List[ImportProduct] = field(default_factory=lambda: [])
    """all import products"""

    module_type: str = "slme"
    """Module type. Supported: slme, minimal, custom"""

    module_type_slme: str = "BOT"
    """SLME module type. Supported: BOT, TOP, STAR"""

    slme_individuals: str = "include"
    """See http://robot.obolibrary.org/extract#syntactic-locality-module-extractor-slme"""

    mirror_retry_download: int = 4
    """Corresponds to the cURL --retry parameter, see http://www.ipgp.fr/~arnaudl/NanoCD/software/win32/curl/docs/curl.html"""

    mirror_max_time_download: int = 200
    """Corresponds to the cURL --max-time parameter (in seconds), see http://www.ipgp.fr/~arnaudl/NanoCD/software/win32/curl/docs/curl.html"""

    release_imports: bool = False
    """If set to True, imports are copied to the release directory."""

    use_base_merging: bool = False
    """If set to true, mirrors will be merged before determining a suitable seed. This can be a quite costly process."""

    base_merge_drop_equivalent_class_axioms: bool = False
    """If set to true, equivalent class axioms will be removed before extracting a module with the base-merging process. Do not activate this feature unless you are positive that your base merging process only leverages true base files, with asserted subclass axioms."""

    exclude_iri_patterns: Optional[List[str]] = None
    """List of IRI patterns. If set, IRIs matching and IRI pattern will be removed from the import."""

    export_obo: bool = False
    """If set to true, modules will not only be created in OWL, but also OBO format"""

    annotation_properties: List[str] = field(
        default_factory=lambda: ["rdfs:label", "IAO:0000115", "OMO:0002000"]
    )
    """Define which annotation properties to pull in."""

    strip_annotation_properties: bool = True
    """If set to true, strip away annotation properties from imports, apart from explicitly imported properties and properties listed in annotation_properties."""

    annotate_defined_by: bool = False
    """If set to true, the annotation rdfs:definedBy is added for each external class. 
       In the case of use_base_merging is also true, this will be added to the imports/merged_import.owl file.
       When imports are not merged, the annotation is added during the release process to the full release artefact.
    """

    scan_signature: bool = True
    """If true, the edit file is scanned for additional terms to import.
       Otherwise, imports are seeded solely from the manually maintained
       *_terms.txt files. Note that setting this option to False makes
       Protégé-based declarations of terms to import impossible.
    """

    def derive_fields(self, project):
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
                    and p.module_type_slme != self.module_type_slme
                )
            ):
                # This module will require a distinct rule
                self.special_products.append(p)


@dataclass_json
@dataclass
class ReportConfig(JsonSchemaMixin):
    """
    A configuration section for ROBOT report
    """

    fail_on: Optional[str] = None
    """see http://robot.obolibrary.org/report#failing for details. """

    use_labels: bool = True
    """see http://robot.obolibrary.org/report#labels for details. """

    use_base_iris: bool = True
    """If true, only reports on problems with entities belonging to this ontology. Set the base_iris using the 'namespaces' at project level."""

    custom_profile: bool = False
    """This will replace the call to the standard OBO report to a custom profile instead."""

    report_on: List[str] = field(default_factory=lambda: ["edit"])
    """Chose which files to run the report on."""

    ensure_owl2dl_profile: bool = True
    """This will ensure that the main .owl release file conforms to the owl2 profile during make test."""

    release_reports: bool = False
    """ If true, release reports are added as assets to the release (top level directory, reports directory)"""

    custom_sparql_checks: Optional[List[str]] = field(
        default_factory=lambda: [
            "owldef-self-reference",
            "iri-range",
            "label-with-iri",
            "multiple-replaced_by",
            "dc-properties",
        ]
    )
    """ Chose which additional sparql checks you want to run. The related sparql query must be named CHECKNAME-violation.sparql, and be placed in the src/sparql directory.
        The custom sparql checks available are: 'owldef-self-reference', 'redundant-subClassOf', 'taxon-range', 'iri-range', 'iri-range-advanced', 'label-with-iri', 'multiple-replaced_by', 'term-tracker-uri', 'illegal-date', 'dc-properties'.
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
    """Chose which custom reports to generate. The related sparql query must be named CHECKNAME.sparql, and be placed in the src/sparql directory."""

    sparql_test_on: List[str] = field(default_factory=lambda: ["edit"])
    """Chose which file to run the custom sparql checks. Supported 'edit', any release artefact."""

    upper_ontology: Optional[str] = None
    """IRI of an upper ontology to check the current ontology against."""


@dataclass_json
@dataclass
class DocumentationGroup(JsonSchemaMixin):
    """
    Setting for the repos documentation system
    """

    documentation_system: Optional[str] = "mkdocs"
    """Currently, only mkdocs is supported. """


@dataclass_json
@dataclass
class ComponentGroup(ProductGroup):
    """
    A configuration section that consists of a list of `ComponentProduct` descriptions

    Controls extraction of import modules via robot extract into the "components/" directory
    """

    products: List[ComponentProduct] = field(default_factory=lambda: [])
    """all component products"""

    def derive_fields(self, project):
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
    """
    A configuration section that consists of a list of `PatternPipelineProduct` descriptions

    Controls the handling of patterns data in the "src/patterns/data" directory
    """

    products: List[PatternPipelineProduct] = field(default_factory=lambda: [])
    """all pipeline products"""

    matches: Optional[List[PatternPipelineProduct]] = None
    """pipelines specifically configured for matching, NOT generating."""


@dataclass_json
@dataclass
class SSSOMMappingSetGroup(JsonSchemaMixin):
    """
    A configuration section that consists of a list of `SSSOMMappingSetProduct` descriptions
    """

    release_mappings: bool = False
    """If set to True, mappings are copied to the release directory."""

    mapping_extractor: str = "sssom-py"
    """The tool to use to extract mappings from an ontology ('sssom-py' or 'sssom-java')."""

    products: List[SSSOMMappingSetProduct] = field(default_factory=lambda: [])

    def derive_fields(self, project):
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
    """
    A configuration section that consists of a list of `BridgeProduct` descriptions
    """

    products: List[BridgeProduct] = field(default_factory=lambda: [])

    def derive_fields(self, project):
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
    """
    A configuration section that consists of a list of `BabelonTranslationProduct` descriptions
    """

    release_merged_translations: bool = False
    """If true, a big table and JSON file is created which contains all translations."""

    predicates: Optional[List[str]] = field(
        default_factory=lambda: ["IAO:0000115", "rdfs:label"]
    )
    """The list of predicates that are considered during translation preparation."""

    oak_adapter: str = "pronto:$(ONT).obo"
    """The oak adapter that should be used to process the translation tables. Should match the 'translate_ontology' field."""

    translate_ontology: str = "$(ONT).obo"
    """The name of the ontology that should be translated. Should match the 'oak_adapter' field."""

    products: Optional[List[BabelonTranslationProduct]] = None


@dataclass_json
@dataclass
class ExportGroup(ProductGroup):
    """
    A configuration section that consists of a list of `ExportProduct` descriptions

    Controls generation of exports (typically SPARQL via robot query) into the "reports/" directory
    """

    products: Optional[List[ExportProduct]] = None
    """all export products"""


@dataclass_json
@dataclass
class RobotPlugin(JsonSchemaMixin):
    """
    A configuration for a single ROBOT plugin
    """

    name: str = ""
    """Basename for the plugin"""

    mirror_from: Optional[str] = None
    """Automatically download the plugin from this URL"""


@dataclass_json
@dataclass
class RobotOptionsGroup(JsonSchemaMixin):
    """
    A configuration section for additional options specific to ROBOT.
    """

    reasoner: str = "ELK"
    """Reasoner to use in robot commands that need one."""

    obo_format_options: str = ""
    """Additional options to pass to robot convert when exporting to OBO. Default is '--clean-obo "strict drop-untranslatable-axioms"'."""

    relax_options: str = "--include-subclass-of true"
    """Additional options to pass to robot relax command."""

    reduce_options: str = "--include-subproperties true"
    """Additional options to pass to robot reduce command."""

    plugins: Optional[List[RobotPlugin]] = None
    """List of ROBOT plugins used by this project."""

    report: Dict[str, Any] = field(default_factory=lambda: ReportConfig().to_dict())
    """Settings for ROBOT report, ROBOT verify and additional reports that are generated."""


@dataclass_json
@dataclass
class OntologyProject(JsonSchemaMixin):
    """
    A configuration for an ontology project/repository

    This is divided into project-wide settings, plus
    groups of products. Products are grouped into 4
    categories (more may be added)
    """

    id: OntologyHandle = ""
    """OBO id for this ontology. Must be lowercase Examples: uberon, go, cl, envo, chebi"""

    config_hash: Optional[str] = None
    """Configuration hash."""

    title: str = ""
    """Concise descriptive text about this ontology"""

    git_user: str = ""
    """GIT user name (necessary for generating releases)"""

    repo: str = "noname"
    """Name of repo (do not include org). E.g. cell-ontology"""

    repo_url: str = ""
    """URL of the online repository. If set, this must point to a browsable version of the repository root."""

    github_org: str = ""
    """Name of github org or username where repo will live. Examples: obophenotype, cmungall"""

    git_main_branch: str = "main"
    """The main branch for your repo, such as main, or (now discouraged) master."""

    edit_format: str = "owl"
    """Format in which the edit file is managed, either obo or owl"""

    run_as_root: bool = False
    """if true, all commands will be executed into the container under the identity of the super-user. Use this if you have custom workflows that require admin rights (e.g. to install Debian packages not provided in the ODK)."""

    robot_version: Optional[str] = None
    """Only set this if you want to pin to a specific robot version"""

    robot_settings: Optional[CommandSettings] = None
    """Settings to pass to ROBOT such as amount of memory to be used"""

    robot_java_args: Optional[str] = ""
    """Java args to pass to ROBOT at runtime, such as -Xmx6G"""

    owltools_memory: Optional[str] = ""
    """OWLTools memory, for example 4GB."""

    use_external_date: bool = False
    """Flag to set if you want odk to use the host `date` rather than the docker internal `date`"""

    remove_owl_nothing: bool = False
    """Flag to set if you want odk to remove owl:Nothing from releases."""

    export_project_yaml: bool = False
    """Flag to set if you want a full project.yaml to be exported, including all the default options."""

    exclude_tautologies: str = "structural"
    """Remove tautologies such as A SubClassOf: owl:Thing or owl:Nothing SubclassOf: A. For more information see http://robot.obolibrary.org/reason#excluding-tautologies"""

    primary_release: str = "full"
    """Which release file should be published as the primary release artefact, i.e. foo.owl"""

    license: str = "https://creativecommons.org/licenses/unspecified"
    """Which license is ontology supplied under - must be an IRI."""

    description: str = "None"
    """Provide a short description of the ontology"""

    use_dosdps: bool = False
    """if true use dead simple owl design patterns"""

    use_templates: bool = False
    """if true use ROBOT templates."""

    use_mappings: bool = False
    """if true use SSSOM mapping files."""

    use_translations: bool = False
    """if true enable babelon multilingual support."""

    use_env_file_docker: bool = False
    """if true environment variables are collected by the docker wrapper and passed into the container."""

    use_custom_import_module: bool = False
    """if true add a custom import module which is managed through a robot template. This can also be used to manage your module seed."""

    manage_import_declarations: bool = True
    """if true, import declarations in the -edit file and redirections in the XML catalog will be entirely managed by the ODK."""

    custom_makefile_header: str = """
# ----------------------------------------
# More information: https://github.com/INCATools/ontology-development-kit/
"""
    """A multiline string that is added to the Makefile"""

    use_context: bool = False
    """If True, a context file is created that allows the user to specify prefixes used across the project."""

    public_release: str = "none"
    """if true add functions to run automated releases (experimental). Current options are: github_curl, github_python."""

    public_release_assets: Optional[List[str]] = None
    """A list of files that gets added to a github/gitlab/etc release (as assets). If this option is not set (None), the standard ODK assets will be deployed."""

    release_date: bool = False
    """if true, releases will be tagged with a release date (oboInOwl:date)"""

    allow_equivalents: str = "asserted-only"
    """can be all, none or asserted-only (see ROBOT documentation: http://robot.obolibrary.org/reason)"""

    ci: Optional[List[str]] = field(default_factory=lambda: ["github_actions"])
    """continuous integration defaults; currently available: travis, github_actions, gitlab-ci"""

    workflows: Optional[List[str]] = field(default_factory=lambda: ["docs", "qc"])
    """Workflows that are synced when updating the repo. Currently available: docs, diff, qc, release-diff."""

    import_pattern_ontology: bool = False
    """if true import pattern.owl"""

    import_component_format: str = "ofn"
    """The default serialisation for all components and imports."""

    create_obo_metadata: bool = True
    """if true OBO Markdown and PURL configs are created."""

    gzip_main: bool = False
    """if true add a gzipped version of the main artefact"""

    release_artefacts: List[str] = field(default_factory=lambda: ["full", "base"])
    """A list of release artefacts you wish to be exported. Supported: base, full, baselite, simple, non-classified, 
    simple-non-classified, basic."""

    release_use_reasoner: bool = True
    """If set to True, the reasoner will be used during the release process. The reasoner is used for three operations:
    reason (the classification/subclassOf hierarchy computation); materialize (the materialisation of simple existential/
    object property restrictions); reduce (the removal of redundant subclassOf axioms)."""

    release_annotate_inferred_axioms: bool = False
    """If set to True, axioms that are inferred during the reasoning process are annotated accordingly, 
    see https://robot.obolibrary.org/reason."""

    release_materialize_object_properties: Optional[List[str]] = None
    """Define which object properties to materialise at release time."""

    export_formats: List[str] = field(default_factory=lambda: ["owl", "obo"])
    """A list of export formats you wish your release artefacts to be exported to, such as owl, obo, gz, ttl, db."""

    namespaces: Optional[List[str]] = None
    """A list of namespaces that are considered at home in this ontology. Used for certain filter commands."""

    use_edit_file_imports: bool = True
    """If True, ODK will release the ontology with imports explicitly specified by owl:imports in the edit file.
    If False, ODK will build and release the ontology with _all_ imports and _all_ components specified in the ODK config file."""

    dosdp_tools_options: str = "--obo-prefixes=true"
    """default parameters for dosdp-tools"""

    travis_emails: Optional[List[Email]] = None  ## ['obo-ci-reports-all@groups.io']
    """Emails to use in travis configurations. """

    catalog_file: str = "catalog-v001.xml"
    """Name of the catalog file to be used by the build."""

    uribase: str = "http://purl.obolibrary.org/obo"
    """Base URI for PURLs. For an example see https://gitlab.c-path.org/c-pathontology/critical-path-ontology."""

    uribase_suffix: Optional[str] = None
    """Suffix for the uri base. If not set, the suffix will be the ontology id by default."""

    contact: Optional[Person] = None
    """Single contact for ontology as required by OBO"""

    creators: Optional[List[Person]] = None
    """List of ontology creators (currently setting this has no effect)"""

    contributors: Optional[List[Person]] = None
    """List of ontology contributors (currently setting this has no effect)"""

    ensure_valid_rdfxml: bool = True
    """When enabled, ensure that any RDF/XML product file is valid"""

    extra_rdfxml_checks: bool = False
    """When enabled, RDF/XML product files are checked against additional parsers"""

    robot: RobotOptionsGroup = field(default_factory=lambda: RobotOptionsGroup())
    """Block for ROBOT-related options"""

    # product groups
    import_group: Optional[ImportGroup] = None
    """Block that includes information on all ontology imports to be generated"""

    components: Optional[ComponentGroup] = None
    """Block that includes information on all ontology components to be generated"""

    documentation: Optional[DocumentationGroup] = None
    """Block that includes information on all ontology components to be generated"""

    subset_group: Optional[SubsetGroup] = None
    """Block that includes information on all subsets (aka slims) to be generated"""

    pattern_pipelines_group: Optional[PatternPipelineGroup] = None
    """Block that includes information on all DOSDP templates used"""

    sssom_mappingset_group: Optional[SSSOMMappingSetGroup] = None
    """Block that includes information on all SSSOM mapping tables used"""

    bridge_group: Optional[BridgeGroup] = None
    """Block that indluces information on all bridges to be generated"""

    babelon_translation_group: Optional[BabelonTranslationSetGroup] = None
    """Block that includes information on all babelon tables used"""

    release_diff: bool = False
    """When enabled, a diff is generated between the current release and the new one"""

    def derive_fields(self):
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

        if not "--clean-obo" in self.robot.obo_format_options:
            if len(self.robot.obo_format_options) > 0:
                self.robot.obo_format_options += " "
            self.robot.obo_format_options += (
                '--clean-obo "strict drop-untranslatable-axioms"'
            )

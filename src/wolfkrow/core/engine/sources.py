
class ResolverException(Exception):
    """ Exception for generic Task errors
    """
    pass

class SourceResolver:
    def __init__(self, sources_config, resolver, sgtk):
        self.sources_config = sources_config
        self.resolver = resolver
        self.sgtk = sgtk

    def resolve_source(self, source):
        """
        Resolves a source defined in the configuration and returns the data for that source.
        The resolution process will depend on the source type and the fields defined for that source in the configuration.
        The resolved data will be used to populate the fields and sequence for the Ingredient.

        Args:
            source (str): The name of the source to resolve.

        Returns:
            dict: A dictionary containing the resolved data for the source, which can be used to populate
                  the fields and sequence for the Ingredient.
        """
        source_config = self.sources_config.get(source)

        if source_config is None:
            raise ResolverException(f"Source '{source}' not found in configuration.")

        source_type = source_config.get("source_type", "").lower()

        if source_type == "sg":
            return self._resolve_sg_source(source, source_config)
        else:
            raise ResolverException(f"Unsupported source type '{source_type}' for source '{source}'.")
        

    def _resolve_sg_source(self, name, source_config):

        resolved_config = self.resolver.resolve(source_config)

        entity_type = resolved_config.get("entity_type")
        query = resolved_config.get("query")
        fields = resolved_config.get("fields", [])
        if entity_type is None or query is None:
            raise ResolverException(f"SG source must have 'entity_type' and 'query' defined in configuration.")

        resolved_query = self.resolver.process_sg_filters(entity_type, query)

        results = self.sgtk.shotgun.find(entity_type, resolved_query, fields)

        if not results:
            raise ResolverException(f"No results found for SG source with entity type '{entity_type}' and query '{resolved_query}'.")
        
        if len(results) > 1:
            print(f"Warning: Multiple results found for SG source with entity type '{entity_type}' and query '{resolved_query}'. Returning the first result.")

        replacements = {
            f"{name}.{field}": results[0].get(field) for field in fields
        }

        return replacements

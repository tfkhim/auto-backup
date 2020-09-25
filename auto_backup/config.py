import inspect


class TaskConfigMerger(object):
    def __init__(self, config):
        self.config = config

    def merge_with_task_config(self, config_section, task_config):
        config_section = self._get_config_section(config_section)

        merged_config = dict()
        merged_config.update(config_section)
        merged_config.update(task_config)
        return merged_config

    def _get_config_section(self, section):
        return self.config.get(section, {})


class MergingTaskFactory(object):
    def __init__(self, factory, merger):
        self.task_factory = factory
        self.merger = merger

    def create(self, task_config):
        merged_config = self._merge_task_and_type_config(task_config)
        return self.task_factory(merged_config)

    def _merge_task_and_type_config(self, task_config):
        return self.merger(task_config)


class TaskFactory(object):
    def __init__(self):
        self.factories = dict()

    def add_task_type(self, type_key, factory):
        self.factories[type_key] = factory

    def add_task_types(self, key_factory_pairs):
        for type_key, factory in key_factory_pairs:
            self.add_task_type(type_key, factory)

    def create(self, type_key, task_config):
        return self.factories[type_key](task_config)


class TaskList(object):
    def __init__(self, task_factory, config):
        self.task_factory = task_factory
        self.config = config
        self.filter_func = lambda t: t

    def __iter__(self):
        created_tasks = map(self.task_factory, self.config)
        return filter(self.filter_func, created_tasks)

    def filter_by_tags(self, tags):
        self.filter_func = lambda t: t.is_active(tags)


class ConfigValueInjector(object):
    def __init__(self, factory):
        self.factory = factory
        self.provided_values = dict()
        self._load_factory_signature_data()

    def _load_factory_signature_data(self):
        parameters = self._get_factory_parameters()
        self._extract_parameter_names(parameters)
        self._extract_default_values(parameters)

    def _get_factory_parameters(self):
        signature = inspect.signature(self.factory)
        return signature.parameters

    def _extract_parameter_names(self, parameters):
        self.parameter_names = list(parameters.keys())

    def _extract_default_values(self, parameters):
        def has_default(parameter):
            return parameter.default != inspect.Signature.empty

        parameters_with_default = filter(has_default, parameters.values())
        self.parameter_defaults = {p.name: p.default for p in parameters_with_default}

    def provide_values(self, **kwargs):
        self.provided_values.update(kwargs)
        return self

    def build(self, config):
        values = self._fetch_values_for_factory_parameters(config)
        return self._create_instance_from_values(values)

    def _fetch_values_for_factory_parameters(self, config):
        return {
            p: self._fetch_value_for_parameter(p, config) for p in self.parameter_names
        }

    def _fetch_value_for_parameter(self, parameter, config):
        value_lookups = self._get_ordered_value_lookups(config)
        self._append_fallback_lookup_for_parameter(value_lookups, parameter)
        lookups_containing_value = filter(lambda s: parameter in s, value_lookups)
        values = map(lambda s: s[parameter], lookups_containing_value)
        return next(values)

    def _get_ordered_value_lookups(self, config):
        return [
            self.provided_values,
            config,
            self.parameter_defaults,
        ]

    def _append_fallback_lookup_for_parameter(self, lookups, parameter):
        lookups.append({parameter: None})

    def _create_instance_from_values(self, values):
        return self.factory(**values)

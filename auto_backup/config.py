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
    def __init__(self, config, notify):
        self.factories = dict()
        self.config = config
        self.notify = notify

    def add_task_type(self, type_key, factory):
        self.factories[type_key] = factory

    def add_task_types(self, key_factory_pairs):
        for type_key, factory in key_factory_pairs:
            self.add_task_type(type_key, factory)

    def create(self, type_key, task_config):
        return self.factories[type_key](task_config, self.notify, self.config)


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

import inspect


class FrameArgumentAssigner(object):
    def __init__(self, stack_entry, target_argument_name):
        self.frame = stack_entry.frame
        self.target_argument_name = target_argument_name
        self._load_frame_info()
        self._load_target_from_frame_info()

    def _load_frame_info(self):
        frame_info = inspect.getargvalues(self.frame)

        self.arguments = frame_info.args
        self.locals = frame_info.locals

    def _load_target_from_frame_info(self):
        self._check_that_target_argument_is_present()
        self._load_target_from_locals()

    def _check_that_target_argument_is_present(self):
        if self.target_argument_name not in self.arguments:
            msg = "No '{}' argument found in function arguments"
            raise KeyError(msg.format(self.target_argument_name))

    def _load_target_from_locals(self):
        self.target = self.locals[self.target_argument_name]

    def assign_arguments_to_target(self):
        for argument in self._relevant_arguments():
            self._assign_argument_to_target(argument)

    def _relevant_arguments(self):
        def is_not_target_argument(argument):
            return argument != self.target_argument_name

        return [a for a in self.arguments if is_not_target_argument(a)]

    def _assign_argument_to_target(self, argument):
        setattr(self.target, argument, self.locals[argument])


def assign_arguments_to_self():
    parent_stack_entry = inspect.stack()[1]
    FrameArgumentAssigner(parent_stack_entry, "self").assign_arguments_to_target()

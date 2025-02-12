import abc


class BaseAction(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def verbose_name(self):
        pass  # pragma: no cover

    @abc.abstractmethod
    def form_valid(self, cmsplugin, instance, request, form):
        pass  # pragma: no cover

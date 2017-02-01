import os
from StringIO import StringIO

from invoke.config import Config as InvokeConfig, merge_dicts
from paramiko.config import SSHConfig

from .util import get_local_user


class Config(InvokeConfig):
    """
    An `invoke.config.Config` subclass with extra Fabric-related behavior.

    This class behaves like `invoke.config.Config` in every way, with the
    following exceptions:

    - its `global_defaults` staticmethod has been extended to add/modify some
      default settings (see its documentation, below, for details);
    - it accepts additional instantiation arguments related to loading
      ``ssh_config`` files.

    Intended for use with `.Connection`, as using vanilla
    `invoke.config.Config` objects would require users to manually define
    ``port``, ``user`` and so forth.

    .. seealso:: :doc:`/concepts/configuration`, :ref:`ssh-config`
    """
    def __init__(self, *args, **kwargs):
        """
        Creates a new Fabric-specific config object.

        For most API details, see `invoke.config.Config.__init__`. Parameters
        new to this subclass are listed below.

        :param ssh_config:
            Custom/explicit `paramiko.config.SSHConfig` object. If given,
            prevents loading of any SSH config files. Default: ``None``.

        :param str runtime_ssh_path:
            Runtime SSH config path to load. Prevents loading of system/user
            files if given. Default: ``None``.

        :param str system_ssh_path:
            Location of the system-level SSH config file. Default:
            ``/etc/ssh/ssh_config``.

        :param str user_ssh_path:
            Location of the user-level SSH config file. Default:
            ``~/.ssh/config``.
        """
        # Tease out our own kwargs.
        # TODO: consider moving more stuff out of __init__ and into methods so
        # there's less of this sort of splat-args + pop thing? Eh.
        ssh_config = kwargs.pop('ssh_config', None)
        # NOTE: due to how DataProxy/InvokeConfig work, setting brand new core
        # attributes requires using object().
        object.__setattr__(self, '_runtime_ssh_path',
            kwargs.pop('runtime_ssh_path', None))
        object.__setattr__(self, '_system_ssh_path',
            kwargs.pop('system_ssh_path', '/etc/ssh/ssh_config'))
        object.__setattr__(self, '_user_ssh_path',
            kwargs.pop('user_ssh_path', '~/.ssh/config'))

        # TODO:
        # - _system_ssh_path (& param, defaults /etc/ssh/ssh_config)
        #   - make clear it's a full path not a prefix or dir
        # - _user_ssh_path (& param, defaults $HOME/.ssh/config)
        # - ssh_config param (defaults None)
        # - ssh_config_path param (defaults None)
        # - load_ssh_files() method, and called after super()
        # - set base_ssh_config attr

        # Super!
        super(Config, self).__init__(*args, **kwargs)
        
        # Arrive at some non-None SSHConfig object.
        explicit_obj_given = ssh_config is not None
        if ssh_config is None:
            ssh_config = SSHConfig()
        #: A `paramiko.config.SSHConfig` object based on loaded config files
        #: (or, if given, the value handed to the ``ssh_config`` param.)
        object.__setattr__(self, 'base_ssh_config', ssh_config)

        # Load files from disk, if necessary
        if not explicit_obj_given:
            self.load_ssh_files()

    def load_ssh_files(self):
        """
        Trigger loading of configured SSH config file paths.

        Expects that `base_ssh_config` has already been set to an `SSHConfig`
        object.

        :returns: ``None``.
        """
        if self._runtime_ssh_path is not None:
            self._load_ssh_file(self._runtime_ssh_path)
        else:
            self._load_ssh_file(self._user_ssh_path)
            self._load_ssh_file(self._system_ssh_path)

    def _load_ssh_file(self, path):
        """
        Attempt to open and parse an SSH config file at ``path``.

        Does nothing if ``path`` is not a path to a valid file.

        :returns: ``None``.
        """
        if os.path.isfile(path):
            with open(path) as fd:
                self.base_ssh_config.parse(fd)

    @staticmethod
    def global_defaults():
        """
        Default configuration values and behavior toggles.

        Fabric only extends this method in order to make minor adjustments and
        additions to Invoke's `~invoke.config.Config.global_defaults`; see its
        documentation for the base values, such as the config subtrees
        controlling behavior of ``run`` or how ``tasks`` behave.

        For Fabric-specific modifications and additions to the Invoke-level
        defaults, see our own config docs at :ref:`default-values`.
        """
        # TODO: is it worth moving all of our 'new' settings to a discrete
        # namespace for cleanliness' sake? e.g. ssh.port, ssh.user etc.
        # It wouldn't actually simplify this code any, but it would make it
        # easier for users to determine what came from which library/repo.
        defaults = InvokeConfig.global_defaults()
        ours = {
            'port': 22,
            'user': get_local_user(),
            'forward_agent': False,
            'run': {
                'replace_env': True,
            },
        }
        merge_dicts(defaults, ours)
        return defaults

"""Resident FunctionFS owner; release shared resources before waiting on its worker."""
import signal


def owner_class():
  from jetlink.comma import owner as comma_owner, root

  class ManagedOwner(comma_owner.Owner):
    def stop_worker(self):
      if self.stop or self.settings.mode() == 'off':
        # Mode-off can stop the process before the upstream next poll restores
        # tuning. Chestnut takeover also needs its host port back immediately.
        self.port.off()
        self.close_link()
        commands = [('vm', 'restore'), ('udc', 'restore')]
        if self.tuned == 'ios':
          commands.append(('draw', 'on'))
        for command in commands:
          if not root.run(*command, timeout=1.0):
            comma_owner.gadget.log.error('Jetlink cleanup failed: %s', command)
        self.tuned = None
      super().stop_worker()

  return ManagedOwner


def main() -> None:
  from jetlink.comma import gadget, owner as comma_owner
  from jetlink.openpilot.owner import worker
  from jetlink.openpilot.settings import FileParams, Settings
  from openpilot.starpilot.models.jetlink_adapter import owner_config
  config = owner_config()
  gadget.set_logger(comma_owner.logger(config.log_file))
  owner = owner_class()(worker(config), cwd=str(config.cwd), env=dict(config.env),
                        settings=Settings(FileParams(config.params_dir), config.keys), chestnut_ids=config.chestnut_ids)
  signal.signal(signal.SIGTERM, owner.request_stop)
  signal.signal(signal.SIGINT, owner.request_stop)
  owner.run()


if __name__ == '__main__':
  main()

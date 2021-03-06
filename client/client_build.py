#!/usr/bin/env python
"""This tool builds or repacks the client binaries.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

import platform
import sys


# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.lib import build
from grr.lib import builders
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup

parser = flags.PARSER

if "32 bit" in sys.version:
  default_arch = "i386"
else:
  default_arch = "amd64"

parser.add_argument(
    "--platform", choices=["darwin", "linux", "windows"],
    default=platform.system().lower(),
    help="The platform to build or repack for. This will default to "
    "the current platform: %s." % platform.system())

parser.add_argument(
    "--arch", choices=["amd64", "i386"],
    default=default_arch,
    help="The architecture to build or repack for.")

parser.add_argument(
    "--package_format", choices=["deb", "rpm"],
    default="deb",
    help="The packaging format to use when building a Linux client.")

# Initialize sub parsers and their arguments.
subparsers = parser.add_subparsers(
    title="subcommands", dest="subparser_name", description="valid subcommands")

# Build arguments.
parser_build = subparsers.add_parser(
    "build", help="Build a client from source.")

parser_repack = subparsers.add_parser(
    "repack", help="Repack a zip file into an installer (Only useful when "
    "signing).")

parser_repack.add_argument("--package", default=None,
                           help="The package zip file to repack.")

parser_repack.add_argument("--output", default=None,
                           help="The path to write the output installer.")

parser_deploy = subparsers.add_parser(
    "deploy", help="Build a deployable self installer from a package.")

parser_deploy.add_argument("--template", default=None,
                           help="The template file to deploy.")

parser_deploy.add_argument("--output", default=None,
                           help="The path to write the output installer.")


parser_deploy.add_argument("-p", "--plugins", default=[], nargs="+",
                           help="Additional python files that will be loaded "
                           "as custom plugins.")

args = parser.parse_args()


def GetBuilder(context):
  """Get the appropriate builder based on the selected flags."""
  try:
    if args.platform == "darwin":
      context.append("Platform:Darwin")
      builder_obj = builders.DarwinClientBuilder

    elif args.platform == "windows":
      context.append("Platform:Windows")
      builder_obj = builders.WindowsClientBuilder

    elif args.platform == "linux":
      context.append("Platform:Linux")
      if args.package_format == "deb":
        builder_obj = builders.LinuxClientBuilder
      else:
        context.append("Target:LinuxRpm")
        builder_obj = builders.CentosClientBuilder

    else:
      parser.error("Unsupported build platform: %s" % args.platform)

  except AttributeError:
    raise RuntimeError("Unable to build for platform %s when running "
                       "on current platform." % args.platform)

  return builder_obj(context=context)


def GetDeployer(context):
  """Get the appropriate client deployer based on the selected flags."""
  if args.platform == "darwin":
    context.append("Platform:Darwin")
    deployer_obj = build.DarwinClientDeployer

  elif args.platform == "windows":
    context.append("Platform:Windows")
    deployer_obj = build.WindowsClientDeployer

  elif args.platform == "linux":
    context.append("Platform:Linux")
    if args.package_format == "deb":
      deployer_obj = build.LinuxClientDeployer
    else:
      context.append("Target:LinuxRpm")
      deployer_obj = build.CentosClientDeployer

  else:
    parser.error("Unsupported build platform: %s" % args.platform)

  return deployer_obj(context=context)


def main(_):
  """Launch the appropriate builder."""
  config_lib.CONFIG.AddContext(
      "ClientBuilder Context",
      "Context applied when we run the client builder script.")

  startup.ClientInit()

  # The following is used to change the identity of the builder based on the
  # target platform.
  context = flags.FLAGS.context
  if args.arch == "amd64":
    context.append("Arch:amd64")
  else:
    context.append("Arch:i386")

  if args.subparser_name == "build":
    builder_obj = GetBuilder(context)
    builder_obj.MakeExecutableTemplate()

  elif args.subparser_name == "repack":
    deployer = GetDeployer(context)
    deployer.RepackInstaller(open(args.package, "rb").read(), args.output)

  elif args.subparser_name == "deploy":
    if args.plugins:
      config_lib.CONFIG.Set("Client.plugins", args.plugins)

    deployer = GetDeployer(context)
    template_path = args.template or config_lib.CONFIG.Get(
        "ClientBuilder.template_path", context=deployer.context)

    deployer.MakeDeployableBinary(template_path, args.output)


if __name__ == "__main__":
  flags.StartMain(main)

"""
A script that crawls and compacts SPF records into IP networks.
This helps to avoid exceeding the DNS lookup limit of the Sender Policy Framework (SPF)
https://tools.ietf.org/html/rfc7208#section-4.6.4
"""
import json
import argparse

import r53spflat

# noinspection PyMissingOrEmptyDocstring
def parse_arguments(config=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Name/path of JSON configuration file (default: spfs.json)",
        default='spfs.json',
        required=False,
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        help="Name/path of output file (default: spf_sums.json)",
        default=None,
        required=False,
    )

    parser.add_argument(
        "--update-records",
        dest='update',
        help="Update SPF records in Route53",
        action="store_true",
        default=False,
        required=False,
    )

    parser.add_argument(
        "--force-update",
        help="Force an update of SPF records in Route53",
        action="store_true",
        dest='force_update',
        default=False,
        required=False,
    )

    parser.add_argument(
        "--no-email",
        help="don't send the email",
        dest='sendemail',
        default=True,
        required=False,
        action="store_false",
    )

    parser.add_argument(
        "--one-record",
        help="force all flattened IPs into one record",
        dest='one_record',
        default=False,
        required=False,
        action="store_true",
    )

    arguments = parser.parse_args()
    if config is not None:
        arguments.config = config
    with open(arguments.config) as config:
        settings = json.load(config)
        arguments.resolvers = settings.get("resolvers",[])
        arguments.toaddr = settings["email"]["to"]
        arguments.fromaddr = settings["email"]["from"]
        arguments.subject = settings["email"].get("subject", 
            "[WARNING] SPF Records for {zone} have changed and should be updated.")
        arguments.update_subject = settings["email"].get("update_subject",
            "[NOTICE] SPF records for {zone} have been updated.")
        arguments.mailserver = settings["email"]["server"]
        arguments.domains = settings["sending domains"]
        if not arguments.output:
            arguments.output = settings.get("output", "spf_sums.json")
        arguments.firstrec = settings.get("first record", "spf0")

    if arguments.sendemail:
        required_non_config_args = all(
            [
                arguments.toaddr,
                arguments.fromaddr,
                arguments.subject,
                arguments.update_subject,
                arguments.mailserver,
                arguments.domains,
            ]
        )
    else:    
        required_non_config_args = all([
            arguments.domains
        ])
    if not required_non_config_args:
        parser.print_help()
        exit()
    if "{zone}" not in arguments.subject:
        raise ValueError("Subject must contain {zone}")
    return arguments


def main(update=None, force_update=None, sendemail=None, one_record=None, config=None):
    args = parse_arguments(config=config)
    if update is not None:
        args.update = update
    if force_update is not None:
        args.force_update = force_update
    if sendemail is not None:
        args.sendemail = sendemail
    if one_record is not None:
        args.one_record = one_record
    r53spflat.main(args)


if __name__ == "__main__":
    main()

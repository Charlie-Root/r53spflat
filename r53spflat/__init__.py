# coding=utf-8
import json
import re
from dns.resolver import Resolver
from sender_policy_flattener.crawler import spf2ips
from sender_policy_flattener.formatting import sequence_hash
from .r53_dns import TXTrec
from .email import email_changes

if "FileNotFoundError" not in locals():
    FileNotFoundError = IOError


def flatten(
    input_records,
    dns_servers,
    email_server,
    email_subject,
    update_subject,
    fromaddress,
    toaddress,
    firstrec,
    update=False,
    email=True,
    lastresult=None,
    force_update=False,
    one_record=False,
    api_key=''
):
    resolver = Resolver()
    if dns_servers:
        resolver.nameservers = dns_servers
    if lastresult is None:
        lastresult = dict()
    current = dict()
    for domain, spf_targets in input_records.items():
        raw_ips = ''
        for target in list(spf_targets.keys()):
            if spf_targets[target] == 'ip':
                raw_ips = raw_ips + target + ' '
                del spf_targets[target]
        records = spf2ips(spf_targets, domain, resolver)
        if one_record:
            # alternative to passing a larger number of bytes in fit_bytes()
            result = 'v=spf1 '
            for record in records:
                record = record[7:]
                result = result + re.split("include:spf.*", record)[0] + '" "'
            if raw_ips:
                result = result[:7] + raw_ips + '" "' + result[7:]
            records = [result[:-3]]
        else:
            # will fail if the last record is too long to insert an include
            records[-1] = records[-1][:-4] + 'include:spf-raw-ips.' + domain + ' -all'
            records.append(f'v=spf1 {raw_ips}-all')
        hashsum = sequence_hash(records)
        current[domain] = {"sum": hashsum, "records": records}
        if lastresult.get(domain, False) and current.get(domain, False):
            previous_sum = lastresult[domain]["sum"]
            current_sum = current[domain]["sum"]
            mismatch = previous_sum != current_sum
            if mismatch:
                print(f'\n***WARNING: SPF changes detected for sender domain {domain}\n')
            else:
                print(f'\nNO SPF changes detected for sender domain {domain}\n')
        
            if mismatch and email:                
                print(f'Sending mis-match details email for sender domain {domain}')
                if update or force_update:
                    thesubject = update_subject
                else:
                    thesubject = email_subject
                email_changes(
                    zone=domain,
                    prev_addrs=lastresult[domain]["records"],
                    curr_addrs=current[domain]["records"],
                    subject=thesubject,
                    server=email_server,
                    fromaddr=fromaddress,
                    toaddr=toaddress,
                    api_key=api_key
                )
            if (mismatch and update) or force_update:
                r53zone = TXTrec(domain)
                numrecs = len(records)
                print(f'\n**** Updating {numrecs} SPF Records for domain {domain}\n')      
                for i in range(0,numrecs):
                    if i == 0:
                        recname = f'{firstrec}.{domain}'
                    elif i == numrecs - 1 and raw_ips and not one_record:
                        recname = f'spf-raw-ips.{domain}'
                    else:
                        recname = f'spf{i}.{domain}'
                    print(f'===> Updating {recname} TXT record..', end='')
                    if r53zone.update(recname, records[i], addok=True, oneline=one_record):
                        print(f'..Successfully updated\n')
                    else:
                        print(f'Failed!\n\n********** WARNING: Update of {recname} TXT record Failed\n')
            

    return current if update or force_update or len(lastresult) == 0 else lastresult


def main(args):
    previous_result = None
    try:
        with open(args.output) as prev_hashes:
            previous_result = json.load(prev_hashes)
    except FileNotFoundError as e:
        print(repr(e))
    except Exception as e:
        print(repr(e))
    finally:
        spf = flatten(
            input_records=args.domains,
            lastresult=previous_result,
            dns_servers=args.resolvers,
            email_server=args.mailserver,
            fromaddress=args.fromaddr,
            toaddress=args.toaddr,
            firstrec=args.firstrec,
            email_subject=args.subject,
            update_subject=args.update_subject,
            update=args.update,
            email=args.sendemail,
            force_update=args.force_update,
            one_record=args.one_record,
            api_key=args.api_key
        )
        with open(args.output, "w+") as f:
            json.dump(spf, f, indent=4, sort_keys=True)

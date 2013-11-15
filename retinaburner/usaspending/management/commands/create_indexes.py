from django.core.management.base import CommandError, BaseCommand
from django.db import connections, transaction
from django.conf import settings
from retinaburner.usaspending.scripts.usaspending.config import INDEX_COLS_BY_TABLE


contracts_idx = """
drop index if exists usaspending_contract_unique_transaction_id;
create index usaspending_contract_unique_transaction_id on usaspending_contract (unique_transaction_id);

drop index if exists usaspending_contract_piid;
create index usaspending_contract_piid on usaspending_contract (piid);

drop index if exists usaspending_contract_district;
create index usaspending_contract_congressionaldistrict on usaspending_contract (statecode, congressionaldistrict);

create index usaspending_contract_dunsnumber on usaspending_contract (dunsnumber);
create index usaspending_contract_signeddate on usaspending_contract (signeddate);

drop index if exists usaspending_contract_fiscal_year;
create index usaspending_contract_fiscal_year on usaspending_contract (fiscal_year);

drop index if exists usaspending_contract_agency_name_ft;
drop index if exists usaspending_contract_contracting_agency_name_ft;
drop index if exists usaspending_contract_requesting_agency_name_ft;
drop index if exists usaspending_contract_vendor_city_ft;
drop index if exists usaspending_contract_vendor_name_ft;

create index usaspending_contract_agency_name_ft on usaspending_contract using gin(to_tsvector('retinaburner', agency_name));
create index usaspending_contract_contracting_agency_name_ft on usaspending_contract using gin(to_tsvector('retinaburner', contracting_agency_name));
create index usaspending_contract_requesting_agency_name_ft on usaspending_contract using gin(to_tsvector('retinaburner', requesting_agency_name));
create index usaspending_contract_vendor_city_ft on usaspending_contract using gin(to_tsvector('retinaburner', city));
create index usaspending_contract_vendor_name_ft on usaspending_contract using gin(to_tsvector('retinaburner', vendorname));

drop index if exists usaspending_contract_defaultsort;
create index usaspending_contract_defaultsort on usaspending_contract (fiscal_year desc, obligatedamount desc);
commit;
"""

grants_idx = """

drop index if exists usaspending_grant_agency_name_ft;
drop index if exists usaspending_grant_recipient_name_ft;

create index usaspending_grant_agency_name_ft on usaspending_grant using gin(to_tsvector('retinaburner', agency_name));
create index usaspending_grant_recipient_name_ft on usaspending_grant using gin(to_tsvector('retinaburner', recipient_name));

create index usaspending_grant_total_funding_amount on usaspending_grant (total_funding_amount);
commit;
"""


class Command(BaseCommand):

    @transaction.commit_on_success
    def handle(self, *args, **kwargs):
        """
        Takes a relation name and a fiscal year and creates a partition for it.
        Current relation names for spending data are:
            usaspending_contract
            usaspending_grant
        """
        grants_base = 'usaspending_grant'
        contracts_base = 'usaspending_contract'

        for fy in settings.FISCAL_YEARS:
            self.create_partition_indexes(contracts_base, "{0}_{1}".format(contracts_base, fy))
            self.create_partition_indexes(grants_base, "{0}_{1}".format(grants_base, fy))

    def create_partition_indexes(self, base_table, partition_name):
        c = connections['default'].cursor()
        for i, colname in enumerate(INDEX_COLS_BY_TABLE[base_table]):
            
            del_stmt = 'drop index if exists {0}_{1}; commit;'.format(partition_name, i)

            if 'using' in colname or '(' in colname:
                idx_stmt = 'create index {0} on {1} {2}; commit;'.format(
                    partition_name + '_{0}'.format(i),
                    partition_name,
                    colname
                )
            else:
                idx_stmt = 'create index {0} on {1} ({2}); commit;'.format(
                    partition_name + '_{0}'.format(i),
                    partition_name,
                    colname
                )
            c.execute(del_stmt)
            c.execute(idx_stmt)

        #create overall indexes 
        print "creating overall contract indexes"
        c.execute(contracts_idx)
        print "creating overall grant indexes"
        c.execute(grants_idx)
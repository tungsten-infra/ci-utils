// Script created for retention of private docker repo on Nexus.
// To use that script change value of repositoryName to the name of cleaned repository.
// Second thing to do is uncomment line 75. That will allow script to delete objects in docker registry.
// Open your Nexus Server -> Server administration and configuration -> Tasks -> Create task -> Admin - Execute script
// -> Choose name of a task -> change Script language to groovy -> set Task frequency -> paste script and save.
import org.sonatype.nexus.repository.storage.StorageFacet;
import org.sonatype.nexus.common.app.GlobalComponentLookupHelper;
import org.sonatype.nexus.repository.maintenance.MaintenanceService;
import org.sonatype.nexus.repository.storage.ComponentMaintenance;
import org.sonatype.nexus.repository.storage.Query;
import org.sonatype.nexus.script.plugin.RepositoryApi;
import org.sonatype.nexus.script.plugin.internal.provisioning.RepositoryApiImpl;
import com.google.common.collect.ImmutableList;
import org.joda.time.DateTime;
import org.slf4j.Logger;

def retentionDays = 15;
def retentionCount = 15;
def tagList = [];
def repositoryName = 'dr-contrail-ci';
def whitelisted_tag_suffixes = ["queens", "ocata", "newton", "latest", "5.0-40", "5.0-94", "5.0-122", "5.0-129", "5.0-161", "5.0-168", "5.0-214", "5.0-309", "5.0-360", "5.0-365"].toArray();
log.info(":::Cleanup script started!");
MaintenanceService service = container.lookup("org.sonatype.nexus.repository.maintenance.MaintenanceService");
def repo = repository.repositoryManager.get(repositoryName);
def tx = repo.facet(StorageFacet.class).txSupplier().get();
def components = null;
try {
    tx.begin();
    components = tx.browseComponents(tx.findBucket(repo));
} catch (Exception e) {
    log.info("Error: " + e);
} finally {
    if (tx != null)
        tx.close();
}

if (components != null) {
    def retentionDate = DateTime.now().minusDays(retentionDays).dayOfMonth().roundFloorCopy();
    int deletedComponentCount = 0;
    def listOfComponents = ImmutableList.copyOf(components);

// comp.version() expected to be in a format {{ os }}-{{ realse }}-{{ branch }}-{{ build }} e.g. rhel-queens-master-386 

    listOfComponents.reverseEach { comp ->
        def tag = comp.version();
        def tagSplited = tag.split("-");
        log.info("tagsplit ${tag} ${tagSplited}");
        def build_number = tagSplited[tagSplited.length - 1];
        // two_parts_build_number is checking correct of build_number with whitelist suffixes
        // covering build number like `5.0.3-0.310` and also different branches from whitelist 5.0 vs 5.1
        def two_parts_build_number = tagSplited[tagSplited.length - 2] + "-" + tagSplited[tagSplited.length - 1];
        log.info("new two parts ${two_parts_build_number}");
        if (whitelisted_tag_suffixes.contains(build_number)) {
            log.info("Component skipped: ${comp.name()} ${comp.version()}");
        } else if (whitelisted_tag_suffixes.contains(two_parts_build_number)){
            log.info("Component skipped: ${comp.name()} ${comp.version()}");
        }else {
            if (!tagList.contains(build_number.toInteger())) {
                tagList.add(build_number.toInteger());
            }
        }
    }
    if(tagList.size() > retentionCount){
        retentionList = tagList.subList(0, tagList.size() - retentionCount);
        listOfComponents.reverseEach { comp ->
        def tag = comp.version();
        def tagSplited = tag.split("-");
        def build_number = tagSplited[tagSplited.length - 1];
        def two_parts_build_number = tagSplited[tagSplited.length - 2] + "-" + tagSplited[tagSplited.length - 1];
        def retentionList = tagList;
        
        if (!whitelisted_tag_suffixes.contains(build_number)) {
            if (!whitelisted_tag_suffixes.contains(two_parts_build_number)) {
                if (retentionList.contains(build_number.toInteger())) {
                    if (comp.lastUpdated() < retentionDate) {
                        log.info("retentionDate: ${comp.lastUpdated()} isOlder ${retentionDate}");
                        log.info("deleting ${comp.name()}, version: ${comp.version()}");
                        // uncomment to delete components and their assets
                        // service.deleteComponent(repo, comp);
                        log.info("----------");
                        deletedComponentCount++;
                    } else {
                        log.info("Component skipped: ${comp.name()} ${comp.version()}");
                    }
                }
            }
        }
    }
        log.info("\n\nDeleted Component count: ${deletedComponentCount} \n");
    } else {
        log.info("Number of builds is already less than ${retentionCount}");
        return true;
    }
}
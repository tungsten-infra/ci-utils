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
def repositoryName = 'BartsDockerRepo';
def whitelisted_tag_suffixes = ["queens", "ocata", "newton", "latest", "40", "94", "122", "129", "161", "214", "309", "360"].toArray();
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
        def build_number = tagSplited[tagSplited.length - 1];

        if (whitelisted_tag_suffixes.contains(build_number)) {
            log.info("Component skipped: ${comp.name()} ${comp.version()}");
        } else {
            if (tagList.count(build_number.toInteger()) == 0) {
                tagList.add(build_number.toInteger());
                println tagList.sort();
            }
        }
    }

    listOfComponents.reverseEach { comp ->
        def tag = comp.version();
        def tagSplited = tag.split("-");
        def build_number = tagSplited[tagSplited.length - 1];
        def retentionList = tagList.subList(0, tagList.size() - retentionCount);

        if (!whitelisted_tag_suffixes.contains(build_number)) {
            if (retentionList.contains(build_number.toInteger())) {
                if (comp.lastUpdated() > retentionDate) {
                    log.info("retentionDate: ${comp.lastUpdated()} isAfter ${retentionDate}");
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
    log.info("\n\nDeleted Component count: ${deletedComponentCount} \n");
}
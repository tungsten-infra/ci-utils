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
    def previousComp = listOfComponents.head().name();

    listOfComponents.reverseEach { comp ->
        def splited = comp.version();
        def spl = splited.split("-");

            if ((spl[spl.length - 1].isNumber()) == true) {
                if (Double.parseDouble(spl[spl.length - 1]) < 1) {
                    String numbers = spl[spl.length - 1].substring(spl[spl.length - 1].length() - 3, spl[spl.length - 1].length());
                    spl[spl.length - 1] = numbers;
                }

            for (j = 0; j < whitelisted_tag_suffixes.length; j++) {
                if (spl[spl.length - 1] == whitelisted_tag_suffixes[j]) {
                    checkValue = true;
                    log.info("Component skipped: ${comp.name()} ${comp.version()}");
                    return checkValue;
                } else {
                    if (whitelisted_tag_suffixes.count(spl[spl.length - 1]) == 0) {
                        if (tagList.count(spl[spl.length - 1].toInteger()) == 0) {
                            tagList.add(spl[spl.length - 1].toInteger());
                            println tagList.sort();
                        }                    
                    }
                }
            }
        }
    }

    listOfComponents.reverseEach { comp ->
        checkValue = null;
        def splited = comp.version();
        def spl = splited.split("-");
        def retentionList = tagList.subList(0, tagList.size() - 15);

        if ((spl[spl.length - 1].isNumber()) == true) {
            if (Double.parseDouble(spl[spl.length - 1]) < 1) {
                spl[spl.length - 1] = spl[spl.length - 1].substring(spl[spl.length - 1].length() - 3, spl[spl.length - 1].length());
            }
        }
        if (whitelisted_tag_suffixes.count(spl[spl.length - 1]) == 0) {
            if (retentionList.count(spl[spl.length - 1].toInteger()) > 0) {
                checkValue = false;
            }
        }
        
        if (checkValue == false) {
            log.info("----------");
            log.info("CompDate: ${comp.lastUpdated()} RetDate: ${retentionDate}");
            if (comp.lastUpdated() > retentionDate) {
                log.info("retentionDate: ${comp.lastUpdated()} isAfter ${retentionDate}");
                log.info("deleting ${comp.name()}, version: ${comp.version()}");
                // ------------------------------------------------
                // uncomment to delete components and their assets
                // service.deleteComponent(repo, comp);
                // ------------------------------------------------
                log.info("----------");
                deletedComponentCount++;
            }
        } else {
            log.info("Component skipped: ${comp.name()} ${comp.version()}");
        }
    }
    log.info("\n\nDeleted Component count: ${deletedComponentCount} \n");
}
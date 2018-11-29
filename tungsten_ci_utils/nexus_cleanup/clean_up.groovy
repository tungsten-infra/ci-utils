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
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.ArrayList;

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
    def checkValue = null;

    listOfComponents.reverseEach {
        comp ->

            def splited = comp.version();
        def spl = splited.split("-");

        for (i = spl.length - 1; i < spl.length; i++) {
            if ((spl[i].isNumber()) == true) {
                if (Double.parseDouble(spl[i]) < 1) {
                    log.info("less than 1")
                    String numbers = spl[i].substring(spl[i].length() - 3, spl[i].length());
                    spl[i] = numbers;
                    log.info(numbers);
                }
            }
            log.info(spl[i])
            checkValue = null;

            for (j = 0; j < whitelisted_tag_suffixes.length; j++) {
                Pattern pattern = Pattern.compile(whitelisted_tag_suffixes[j]);
                Matcher matcher = pattern.matcher(spl[i]);
                boolean found = matcher.matches();
                if (found == true) {
                    log.info("true " + j);
                    checkValue = true;
                    log.info("Component skipped: ${comp.name()} ${comp.version()}");
                    return checkValue;
                } else {
                    if (whitelisted_tag_suffixes.count(spl[i]) == 0) {
                        if (spl[i].toInteger() > 1) {
                            if (tagList.count(spl[i].toInteger()) == 0) {
                                tagList.add(spl[i].toInteger());
                                println tagList.sort();

                            }
                        } else {
                            tagList.add(Double.parseDouble(spl[i]));
                        }
                    }
                }
            }
        }
    }

    listOfComponents.reverseEach {
        comp ->
            checkValue = null;
        def splited = comp.version();
        def spl = splited.split("-");
        def retentionList = tagList.subList(0, tagList.size() - 15);
        for (i = spl.length - 1; i < spl.length; i++) {
            if ((spl[i].isNumber()) == true) {
                if (Double.parseDouble(spl[i]) < 1) {
                    spl[i] = spl[i].substring(spl[i].length() - 3, spl[i].length());
                }
            }
            if (whitelisted_tag_suffixes.count(spl[i]) == 0) {
                log.info("whitelist clear")
                if (retentionList.count(spl[i].toInteger()) > 0) {
                    log.info("false")
                    checkValue = false;
                }
            }
        }
        println retentionList;
        log.info(String.valueOf(checkValue))
        if (checkValue == false) {
            log.info("CompDate: ${comp.lastUpdated()} RetDate: ${retentionDate}");
            if (comp.lastUpdated() > retentionDate) {
                log.info("compDate after retentionDate: ${comp.lastUpdated()} isAfter ${retentionDate}");
                log.info("deleting ${comp.name()}, version: ${comp.version()}");
                // ------------------------------------------------
                // uncomment to delete components and their assets
                // service.deleteComponent(repo, comp);
                // ------------------------------------------------
                log.info("component deleted");
                log.info("----------");
                deletedComponentCount++;
            }
        } else {
            log.info("Component skipped: ${comp.name()} ${comp.version()}");
        }
    }

    log.info("----------");
    log.info("Deleted Component count: ${deletedComponentCount}");
    log.info("----------");
}
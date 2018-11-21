import org.sonatype.nexus.repository.storage.StorageFacet;
import org.sonatype.nexus.common.app.GlobalComponentLookupHelper
import org.sonatype.nexus.repository.maintenance.MaintenanceService
import org.sonatype.nexus.repository.storage.ComponentMaintenance
import org.sonatype.nexus.repository.storage.Query;
import org.sonatype.nexus.script.plugin.RepositoryApi
import org.sonatype.nexus.script.plugin.internal.provisioning.RepositoryApiImpl
import com.google.common.collect.ImmutableList
import org.joda.time.DateTime;
import org.slf4j.Logger
import java.util.regex.Matcher
import java.util.regex.Pattern

def retentionDays = 15;
def retentionCount = 15;
def repositoryName = 'BartsDockerRepo';
def core = ["ocata", "newton", "queens", "latest"].toArray();
def whitelisted_tag_suffixes = ["latest", "ocata", "newton", "queens", "latest","40", "94", "122", "129", "161", "214", "309", "360"].toArray();

log.info(":::Cleanup script started!");
MaintenanceService service = container.lookup("org.sonatype.nexus.repository.maintenance.MaintenanceService");
def repo = repository.repositoryManager.get(repositoryName);
def tx = repo.facet(StorageFacet.class).txSupplier().get();
def components = null;
try {
    tx.begin();
    components = tx.browseComponents(tx.findBucket(repo));
}catch(Exception e){
    log.info("Error: "+e);
}finally{
    if(tx!=null)
        tx.close();
}

if(components != null) {
    def retentionDate = DateTime.now().minusDays(retentionDays).dayOfMonth().roundFloorCopy();
    int deletedComponentCount = 0;
    int compCount = 0;
    def listOfComponents = ImmutableList.copyOf(components);
    def previousComp = listOfComponents.head().name();
    def coreList = [0,0,0,0];
    def fruitEnd = true;
    listOfComponents.reverseEach{comp ->

        def splited = comp.version();
        def spl = splited.split("-");
        for (i = 0; i < core.length; i++) {
            fruitEnd = true;
            log.info(comp.name() + " " + core[i]);
            if (comp.name() == core[i]) {
                coreList[i]++;
                if (coreList[i] > retentionCount) {
                    for (j = spl.length - 1; j < spl.length; j++) {
                        for (k = 0; k < whitelisted_tag_suffixes.length; k++) {
                            def fruit = whitelisted_tag_suffixes.collect { item -> item.contains(spl[j])}
                            if (fruit[k] == true) {
                                fruitEnd = true;
                                log.info(spl[j] + " true");
                                return fruitEnd;
                            } else {
                                fruitEnd = false;
                                log.info(spl[j] + " false");
                            }
                            
                        }
                        
                    }

                }

                if(fruitEnd == false){

                    log.info("CompDate: ${comp.lastUpdated()} RetDate: ${retentionDate}");
                    if(comp.lastUpdated().isBefore(retentionDate)) {
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
        }else{
            log.info("Component skipped: ${comp.name()} ${comp.version()}");
        }
            } else {
                log.info('wuuuuut')
            }

        }        
    }
    log.info("----------");
    log.info("Deleted Component count: ${deletedComponentCount}");
    log.info("----------");
}

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

def retentionCount = 15;
def retentionDays = 30;
def repositoryName = 'BartsDockerRepo';
def whitelistCore = ["latest", "ocata", "newton"].toArray();
def whitelist = ["latest","40", "94", "122", "129", "161", "214", "309"].toArray();

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
    listOfComponents.reverseEach{comp ->

        log.info("Processing Component - ${comp.name()}, version: ${comp.version()}");
        log.info("----------");
        def fruitEnd = "null";
        for(i = 0; i < whitelistCore.length; i++){
            def fruitJuice = whitelistCore.collect{item -> item.contains(comp.version())}
            
            if(fruitJuice[i] == true){
                fruitEnd = "true";
                log.info("Fruit Juice! "+ fruitJuice[i] + " " + comp.version());
                log.info("----------");
                return fruitEnd;
            }else{
            
                def splited = comp.version();
                def spl = splited.split("-");

                for(j = 0; j < spl.length; j++ ){            
                    for(k = 0; k < whitelist.length; k++){
                        def fruit = whitelist.collect{item -> item.contains(spl[j])}
                        if(fruit[k] == true){
                            fruitEnd = "true";
                            log.info(spl[j]+ " true");
                            return fruitEnd;
                        }else{
                            fruitEnd = "false";
                            log.info(spl[j]+ " false");
                        }
                    }
                }
            }
        }
        log.info("----------");
        log.info(fruitEnd + " Result");
        log.info("----------");


        if(fruitEnd == "false"){
            log.info("am I?");
            log.info(previousComp);

            if(previousComp.equals(comp.name())) {
            // for test purposes check of prev name commented out
            
            // if(fruitEnd == "false"){
                compCount++;
                log.info("ComCount: ${compCount}, ReteCount: ${retentionCount}");

                if (compCount > retentionCount) {
                    log.info("CompDate: ${comp.lastUpdated()} RetDate: ${retentionDate}");
                    if(comp.lastUpdated().isBefore(retentionDate)) {
                        log.info("compDate after retentionDate: ${comp.lastUpdated()} isAfter ${retentionDate}");
                        log.info("deleting ${comp.group()}, ${comp.name()}, version: ${comp.version()}");

                        // ------------------------------------------------
                        // uncomment to delete components and their assets
                        // service.deleteComponent(repo, comp);
                        // ------------------------------------------------

                        log.info("component deleted");
                        log.info("----------");
                        deletedComponentCount++;
                    }
                }
            } else {
                compCount = 1;
                previousComp = comp.name();
            }
        }else{
            log.info("Component skipped: ${comp.name()}");
        }
    }
    log.info("----------");
    log.info("Deleted Component count: ${deletedComponentCount}");
    log.info("----------");
}

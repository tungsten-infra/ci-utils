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

def retentionCount = 0;
def retentionDays = 0;
def repositoryName = 'BartsDockerRepo';
def whitelist = ["latest", "ocata", "newton"].toArray();


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
        
        // log.info(fruit);
        def fruitEnd = "null";
        def splited = comp.version();
        def spl = splited.split("-");

        for(i = 0; i < spl.length; i++ ){
            
            for(j = 0; j < whitelist.length; j++){
                def fruit = whitelist.collect{item -> item.contains(spl[i])}
                if(fruit[j] == true){
                    fruitEnd = "true";
                    log.info(spl[i]);
                    log.info("true");
                    return fruitEnd;
                }else{
                    fruitEnd = "false";
                    log.info("false");
                    log.info(spl[i]);
                }
            }
        }

        log.info("----------");
        log.info(fruitEnd);
        log.info("----------");
        log.info("result");


        if(fruitEnd == "false"){
            log.info("am I?");
            log.info(previousComp);

            // if(previousComp.equals(comp.name())) {
            // for test purposes check of prev name commented out
            
            if(fruitEnd == "false"){
                compCount++;
                log.info("ComCount: ${compCount}, ReteCount: ${retentionCount}");

                if (compCount > retentionCount) {
                    log.info("CompDate: ${comp.lastUpdated()} RetDate: ${retentionDate}");
                    // if(comp.lastUpdated().isBefore(retentionDate)) {
                        log.info("compDate after retentionDate: ${comp.lastUpdated()} isAfter ${retentionDate}");
                        log.info("deleting ${comp.group()}, ${comp.name()}, version: ${comp.version()}");

                        // ------------------------------------------------
                        // uncomment to delete components and their assets
                        // service.deleteComponent(repo, comp);
                        // ------------------------------------------------

                        log.info("component deleted");
                        deletedComponentCount++;
                    // }
                }
            } else {
                compCount = 1;
                previousComp = comp.name();
            }
        }else{
            log.info("Component skipped: ${comp.name()}");
        }
    }

    log.info("Deleted Component count: ${deletedComponentCount}");
}

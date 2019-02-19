// Script created for cleaning empty yum repos with just repodata on Nexus.
// To use that script change value of repositoryName to the name of cleaning repository.
// Second thing to do is uncomment line 44 and 48. That will allow script to delete assets in repository.
// Open your Nexus Server -> Server administration and configuration -> Tasks -> Create task -> Admin - Execute script
// -> Choose name of a task -> change Script language to groovy -> set Task frequency -> paste script and save.
import org.sonatype.nexus.repository.storage.Asset
import org.sonatype.nexus.repository.storage.Query
import org.sonatype.nexus.repository.storage.StorageFacet
import org.sonatype.nexus.repository.raw.internal.RawFormat
import org.joda.time.DateTime;

import groovy.json.JsonOutput
import groovy.json.JsonSlurper

def request = new JsonSlurper().parseText("{\"repoName\":\"yum-tungsten\",\"startDate\":\"2018-01-01\"}");

assert request.repoName: 'repoName parameter is required';
assert request.startDate: 'startDate parameter is required, format: yyyy-mm-dd';


def repo = repository.repositoryManager.get(request.repoName);

assert repo: "Repository ${request.repoName} does not exist";
def retentionDays = 14;
def retentionDate = DateTime.now().minusDays(retentionDays).dayOfMonth().roundFloorCopy();
StorageFacet storageFacet = repo.facet(StorageFacet);
def counter = 0;
def tx = storageFacet.txSupplier().get();
try {
    tx.begin()

    Iterable<Asset> assets = tx.
        findAssets(Query.builder().where('last_updated > ').param(request.startDate).build(), [repo])

    def urls = assets.collect { "/repository/${repo.name}/${it.name()}" }

    assets.each { asset ->
        def name = asset.name();
        def nameSplited = name.split("/");
        if(nameSplited.length.toString() == '3'){
            if(asset.lastUpdated() < retentionDate){
                log.info("Deleting asset ${asset.name()}")
                counter++;
                // tx.deleteAsset(asset);
                if (asset.componentId() != null) {
                    log.info("Deleting component for asset ${asset.name()}")
                    def component = tx.findComponent(asset.componentId());
                    // tx.deleteComponent(component);
                }
            }
        }
    }
    log.info(counter.toString());
    tx.commit()

} catch (Exception e) {
    log.warn("Error occurs while deleting snapshot images from docker repository: {}", e.toString())
    tx.rollback()
} finally {
    tx.close()
}
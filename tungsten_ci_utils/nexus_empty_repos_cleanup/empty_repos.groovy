import org.sonatype.nexus.repository.storage.Asset
import org.sonatype.nexus.repository.storage.Query
import org.sonatype.nexus.repository.storage.StorageFacet
import org.sonatype.nexus.repository.raw.internal.RawFormat

import groovy.json.JsonOutput
import groovy.json.JsonSlurper

def request = new JsonSlurper().parseText("{\"repoName\":\"yum-tungsten\",\"startDate\":\"2019-01-01\"}");

assert request.repoName: 'repoName parameter is required';
assert request.startDate: 'startDate parameter is required, format: yyyy-mm-dd';


def repo = repository.repositoryManager.get(request.repoName);

assert repo: "Repository ${request.repoName} does not exist";

StorageFacet storageFacet = repo.facet(StorageFacet);
def tx = storageFacet.txSupplier().get();
try {
    tx.begin()

    Iterable<Asset> assets = tx.
        findAssets(Query.builder().where('last_updated > ').param(request.startDate).build(), [repo])

    def urls = assets.collect { "/repository/${repo.name}/${it.name()}" }

    assets.each { asset ->
        log.info("Deleting asset ${asset.name()}")
        // tx.deleteAsset(asset);
        if (asset.componentId() != null) {
            log.info("Deleting component for asset ${asset.name()}")
            def component = tx.findComponent(asset.componentId());
            // tx.deleteComponent(component);
        }
    }

    tx.commit()

    // def result = JsonOutput.toJson([
    //     assets    : urls,
    //     // assetName : request.assetName,
    //     repoName  : request.repoName
    // ])
    // return result

} catch (Exception e) {
    log.warn("Error occurs while deleting snapshot images from docker repository: {}", e.toString())
    tx.rollback()
} finally {
    tx.close()
}
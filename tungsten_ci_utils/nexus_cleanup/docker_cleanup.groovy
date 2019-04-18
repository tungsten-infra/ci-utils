// 
// Custom cleanup of docker registry on Nexus
//
// Initially use dryRun=true, so no deletion actually happens
// 

def dryRun = true ;
def repositoriesToClean = [ 
    [repositoryName: 'dr-tungsten-ci',        retentionHours: 160*24+7],
    [repositoryName: 'dr-tungsten-nightly',   retentionHours: 100*24+7]
];

//
// Authoritative version at:
//     https://github.com/tungsten-infra/ci-utils/tungsten_ci_utils/nexus_cleanup/docker_cleanup.groovy
// 
// Manual changes will be OVERWRITTEN.
//
// Deploy this script with the Nexus WebUI:
//     Menu -> Server Administration and Configuration -> Tasks -> Create task -> Admin - Execute script -> paste script
//
/////// Design of this /////////////////
//
//  Requirement: For an existing image:tag, the `docker push image:tag` always postpones deletion, even if hash is identical.
//    (This is *not* true for lastModified and lastDownloaded as tested on Nexus 3.14. Only the asset-level last_modified attribute solves it.) 
// 
//  Requirement: Support retention with hour granularity.
//  
////////////////////////////////////////

import org.joda.time.DateTime;
import com.google.common.collect.ImmutableList;
import org.sonatype.nexus.repository.storage.StorageFacet;
import org.sonatype.nexus.repository.maintenance.MaintenanceService;
import org.sonatype.nexus.repository.storage.Asset;
import org.sonatype.nexus.repository.docker.DockerGCFacet ;
import org.sonatype.nexus.repository.docker.internal.DockerGCFacetImpl ;
import static org.sonatype.nexus.common.time.DateHelper.toDateTime;


for(repoToClean in repositoriesToClean) {
    def repositoryName = repoToClean.repositoryName;
    def retentionDate = DateTime.now().minusHours(repoToClean.retentionHours);
    log.info(":::Cleanup script started for ${repositoryName} with the retention date ${retentionDate}");

    MaintenanceService service = container.lookup("org.sonatype.nexus.repository.maintenance.MaintenanceService");
    def repo = repository.repositoryManager.get(repositoryName);
    def tx = repo.facet(StorageFacet.class).txSupplier().get();
    try {
        tx.begin();
        def assets = tx.browseAssets(tx.findBucket(repo));
        tx.rollback()
        int deletedComponentCount = 0
        int skippedComponentCount = 0
        def keepingComponents = [:];
        ImmutableList.copyOf(assets).each{ asset ->
            if(asset.componentId() != null) {
                def ch = asset.attributes().child("content");
                //log.info("ch=${ch}");
                //log.info("a.m=${asset.getEntityMetadata()}");
                //def ldo = asset.lastDownloaded();
                def last_modified = toDateTime(ch.get("last_modified",Date.class));
                if(last_modified >= retentionDate)  {
                    log.debug("Asset ${asset.name()} last_modified ${last_modified} is after ${retentionDate}, keeping ${asset.componentId()}");
                    keepingComponents[asset.componentId()]=true;
                } else if(keepingComponents[asset.componentId()]) {
                    log.info("Asset ${asset.name()} last_modified ${last_modified} is ignored as it belongs to ${asset.componentId()} which is kept");
                } else {
                    tx.begin();
                    def comp = tx.findComponentInBucket(asset.componentId(),tx.findBucket(repo));
                    tx.rollback();
                    if(comp != null) {
                        if (comp.lastUpdated() < retentionDate) {
                            log.info("Deleting ${repositoryName}/${comp.name()}:${comp.version()}, changed ${comp.lastUpdated()}, pushed ${last_modified}: both before ${retentionDate}");
                            if(!dryRun) {
                                service.deleteComponent(repo, comp);
                            }
                            deletedComponentCount++;
                        } else {
                            log.info("Skipping ${repositoryName}/${comp.name()}:${comp.version()}, changed ${comp.lastUpdated()}: pushed ${last_modified} after ${retentionDate}");
                            skippedComponentCount++;
                        }
                    }
                }
            }
        }
        log.info("Deleted ${deletedComponentCount} docker image-tags from ${repositoryName}");
        log.info("Keeping ${keepingComponents.size()} image-tags which had recent assets");
        log.info("Skipped ${skippedComponentCount} recent image-tags which had old assets");

        //ImmutableList.copyOf(components).each { comp ->
        //    if (comp.lastUpdated() < retentionDate) {
        //        if(goodComponents[comp] != null) {
        //            log.info("Keeping  ${repositoryName}/${comp.name()}:${comp.version()}, changed ${comp.lastUpdated()}, but recently re-pushed");
        //        } else {
        //            log.info("Deleting ${repositoryName}/${comp.name()}:${comp.version()}, changed ${comp.lastUpdated()}, older than ${retentionDate}");
        //            if(!dryRun) {
        //                service.deleteComponent(repo, comp);
        //            }
        //            deletedComponentCount++;
        //        }
        //    } else {
        //        log.debug("Skipping ${repositoryName}/${comp.name()}:${comp.version()}, changed ${comp.lastUpdated()}");
        //    }
        //}
    } finally {
        tx.close();     // Important: close() must always follow begin(), as there is no transaction cleanup.
                        // Repository will *fail* all begin() calls until restart.
                        // https://stackoverflow.com/questions/52717202/nexus-oss-v3-12-1-01-groovy-script-fails-with-nested-db-tx
    }
    log.info("'Docker - delete unused manifests and images' starting on ${repositoryName}");
    def dockergc = repo.facet(DockerGCFacet.class);
    if(!dryRun) {
        dockergc.deleteUnusedManifestsAndImages();
    }
    log.info("'Docker - delete unused manifests and images' completed on ${repositoryName}");
}


// 
// Cleanup of error 'DockerGCFacetImpl - Unable to read V2 Manifest for asset....name:v2/-/blobs/...' where BLOB is mistakenly marked MANIFEST
//

def repositoryName = "dr-tungsten-ci";
def problematicBlob = 'v2/-/blobs/sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4';

// 
// Authoritative version at:
//     https://github.com/tungsten-infra/ci-utils/tungsten_ci_utils/nexus_cleanup
// 
// Manual changes will be OVERWRITTEN.
//
// Deploy this script with the Nexus WebUI:
//     Menu -> Server Administration and Configuration -> Tasks -> Create task -> Admin - Execute script -> paste script
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

log.info("Fix script started for ${repositoryName}");

MaintenanceService service = container.lookup("org.sonatype.nexus.repository.maintenance.MaintenanceService");
def repo = repository.repositoryManager.get(repositoryName);
def tx = repo.facet(StorageFacet.class).txSupplier().get();
try {
    tx.begin();
    def a = tx.findAssetWithProperty('name',problematicBlob);
    def at = a.attributes();
    log.info("problematic ${at.child('docker').get('asset_kind')}");
    if( at.child('docker').get('asset_kind') == 'MANIFEST' ) {
        at.child('docker').set('asset_kind','BLOB');
        log.info("problematic ${at}");
        tx.saveAsset(a);
    }
    tx.commit();
    log.info("Fix script committed for ${repositoryName}");
} finally {
    tx.close();     // Important: close() must always follow begin(), as there is no transaction cleanup.
                    // Repository will *fail* all begin() calls until restart.
                    // https://stackoverflow.com/questions/52717202/nexus-oss-v3-12-1-01-groovy-script-fails-with-nested-db-tx
}


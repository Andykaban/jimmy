import groovy.json.JsonSlurper

def jsonSlurper = new JsonSlurper()
def parsedArgs = jsonSlurper.parseText(args[0])

for (node in parsedArgs) {
    if (node.key.equals("master")) {
        jenkinsNode = jenkins.model.Jenkins.instance
    } else {
        jenkinsNode = jenkins.model.Jenkins.instance.getNode(node.key)
    }
    if (jenkinsNode != null) {
        println("Update node: " + node.key)
        if (node.value.size() == 0) {
            println("Labels list is empty, nothing to do...")
            continue
        }
        newLabelString = node.value.join(" ")
        println("Adding labels '" + newLabelString + "' from node " + node.key)
        jenkinsNode.setLabelString(newLabelString)
        jenkinsNode.save()
    }
}

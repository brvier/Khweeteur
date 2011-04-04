import Qt 4.7
 
ListView {
    id: tweetsList
    width: 800
    height: 600
 
    model: tweetsListModel
 
    delegate: Component {
        Rectangle {
            width: tweetsList.width
            color: ((index % 2 == 0)?"#222":"#111")
            height: 120
        Image {
            id: tweetAvatar;
            source: model.status.avatar
            anchors {
                left: parent.left
                leftMargin: 5
                top: parent.top
                topMargin: 5
                bottomMargin: 5
                rightMargin: 5
            }
            width:70; height:70
        }
        Text {
            id: tweetText
            anchors.top: tweetAvatar.top
            anchors.left: tweetAvatar.right
            anchors.bottom: tweetAvatar.bottom
            anchors.leftMargin: 20
            anchors.right: parent.right
            anchors.rightMargin: 20
            font.pixelSize: 24
            clip: true
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
            text: model.status.text
            color: "white"
            onLinkActivated: handleLink (link)
        }
        Text {
            anchors.top: tweetText.bottom
            anchors.left: tweetText.left
            anchors.bottom: parent.bottom
            anchors.topMargin: 4
            font.pixelSize: 12
            clip: true
            width: tweetText.width
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
            text: "<html><span style=\"color:#779dca\">"+model.status.created_at+" by "+model.status.screen_name+"</span>"
        }
        function handleLink (link) {
            console.log("link: "+link)
            if (link.slice(0,4) == 'http') {
                Qt.openUrlExternally (link);
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: { controller.statusSelected(model.status) }
        }
        }
    }
}
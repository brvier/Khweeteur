import Qt 4.7

Rectangle {
    id: container
    //width: parent.width
    //height: parent.height
 
    ListView {
        id: tweetsList
        width: parent.width
        height: parent.height
     
        model: tweetsListModel
     
        delegate: Component {
            Rectangle {
                width: tweetsList.width
                color: ((index % 2 == 0)?"#222":"#111")
                //height:(((tweetText.height+27)>90)?tweetText.height+27:90)
                height:(((tweetText.height + 40)>80)?tweetText.height+40:80)
                Image {
                    id: tweetAvatar;
                    source: model.status.avatar
                    x:5;y:10
                    width:60; height:60
                }
                Text {
                    id: tweetText
                    x:70;y:5
                    font.pixelSize: 24
                    //clip: true
                    width:parent.width - 85
                    wrapMode: Text.WordWrap
                    textFormat: Text.RichText
                    text: model.status.text
                    color: "white"
                    onLinkActivated: handleLink (link)
                }
                Text {
                    id:tweetDetails
                    height: 20
                    x:70
                    width:parent.width - 85
                    anchors.top: tweetText.bottom
                    anchors.bottom: parent.bottom
                    anchors.topMargin: 5
                    font.pixelSize: 12
                    //clip: true
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

    Rectangle {
        id: picker

        width: container.width; height: 64
        anchors.bottom: container.bottom

        gradient: Gradient {
            GradientStop { position: 0.5; color: "#CC343434" }
            GradientStop { position: 1.0; color: "#66000000" }
        }

        ListView {
            id: view

            anchors.fill: parent; anchors.rightMargin: 200
            model: toolbarListModel
            spacing: 10
            orientation: "Horizontal"
            
        delegate: Component {
            Item {
                width: action.width + image.width;
                height: 60
                Rectangle {
                    id: pickerItem

                    x: 10; y: 2
                    width: parent.width;
                    height: 60
                    focus: true

                    opacity: 0.7
                    //radius: 5
                    //border.width: 0; //border.color: "#AA444444"
                    //color: "#FF444444"
                    radius: 5
                    border.color: "#AA444444"; border.width: 1
                    
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#AA999999" }
                        GradientStop { position: 1.0; color: "#AA333333" }
                    }

                    Text {
                        id: action
                        anchors.centerIn: parent
                        text: model.button.label
                        color: "white"
                        visible: (model.button.src=="")
                        opacity: 0.7
                        }

                    Image {
                        id: image
                        opacity: 0.7
                        x: 1; y: 1
                        width: 60; height: pickerItem.height - 2
                        source: model.button.src
                        asynchronous: true
                        visible: (model.button.label=="")
                    }

                    Rectangle {
                        id: newPostIt
                        x:parent.x+parent.width-40
                        y:parent.y
                        width:30
                        height:30
                        color: "red"
                        radius:5
                        visible: (model.button.count>0)
                        opacity: 1
                        Text {
                            id: newPostItText
                            anchors.centerIn: parent
                            text: model.button.count
                            color: "white"
                            visible: (model.button.count>0)
                            opacity: 1
                        }
                        }
                                            
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { view.currentIndex = index; controller.toolbar_callback(model.button.src+model.button.label); }
                    }

                    states: [
                        State {
                            name: "selected"
                            when: ListView.isCurrentItem
                            PropertyChanges { target: image; opacity: 1 }
                            PropertyChanges { target: newPostIt; visible: false }
                            //PropertyChanges { target: count: 0 }
                            PropertyChanges { target: pickerItem; opacity: 1; border.color: "black" }
                            //StateChangeScript { script: bigImage.source = image.source }
                        }
                    ]

                    transitions: Transition {
                        from: "*"
                        to: "selected"
                        reversible: true
                        NumberAnimation { duration: 250; easing.type: "OutCirc"; properties: "opacity,rotation" }
                    }
                }
            }}
        }

        states: State {
            name: "hidden"
            when: hider.hidden
            PropertyChanges { target: picker; opacity: 0.1; height: 0 }
            //PropertyChanges { target: imageName; opacity: 0 }
        }

        transitions: Transition {
            from: "*"; to: "hidden"; reversible: true
            NumberAnimation { easing.type: "InOutQuad"; properties: "opacity, height"; duration: 500 }
        }
        
    }

    Rectangle {
        id:input
        //property bool hidden: true
        visible: false
        width: parent.width; height: 60
        radius: 5
        border.color: "#AA444444"; border.width: 1

        Behavior on opacity { NumberAnimation { } }

        gradient: Gradient {
            GradientStop { position: 0.0; color: "#AA999999" }
            GradientStop { position: 1.0; color: "#AA333333" }
        }
        TextInput {
                id: editTweet

                text: "test"
                anchors { left: parent.left; margins: 10; verticalCenter: parent.verticalCenter; right: parent.right }
                color: "black"
                font.pixelSize: parent.height - 13
            }
    }
    
    Rectangle {
        id: hider

        property bool hidden: false

        width: 60; height: 60
        anchors { right: parent.right; bottom: parent.bottom; rightMargin: 4; bottomMargin: 2 }
        radius: 5
        border.color: "#AA444444"; border.width: 1

        Behavior on opacity { NumberAnimation { } }

        gradient: Gradient {
            GradientStop { position: 0.0; color: "#AA999999" }
            GradientStop { position: 1.0; color: "#AA333333" }
        }

        Text {
            id: hiderText
            anchors.centerIn: parent
            text: "Hide"
            color: "white"
        }

        MouseArea {
            anchors.fill: parent
            onClicked: { hider.hidden = !hider.hidden }
        }

        states: State {
            name: "hidden"
            when: hider.hidden
            PropertyChanges { target: hiderText; text: "Show" }
            PropertyChanges { target: hider; opacity: 0.4 }
//            PropertyChanges { target: slider; opacity: 0.4 }
        }
    }
}    
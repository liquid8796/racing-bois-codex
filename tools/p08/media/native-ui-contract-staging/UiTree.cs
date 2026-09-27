using System;
using System.Globalization;
using System.Xml.Linq;
using UnityEngine.UIElements;

namespace RacingBois.Tools.NativeUi
{
    internal static class UiTree
    {
        // Preserve real UXML declarations but never load USS, font assets, PanelSettings or an attached panel.
        // This is a binding/state fixture, not validation of Unity's UXML importer or CSS/layout/rendering.
        public static void Populate(VisualElement root, string path)
        { foreach (var element in XDocument.Load(path).Root.Elements()) if (element.Name.LocalName != "Style") root.Add(Create(element)); }
        private static VisualElement Create(XElement node)
        {
            VisualElement element;
            switch (node.Name.LocalName)
            {
                case "VisualElement": element = new VisualElement(); break;
                case "ScrollView": element = new ScrollView(); break;
                case "Label": element = new Label((string)node.Attribute("text") ?? ""); break;
                case "Button": element = new Button { text = (string)node.Attribute("text") ?? "" }; break;
                case "TextField": element = new TextField { value = (string)node.Attribute("value") ?? "", isReadOnly = (string)node.Attribute("is-read-only") == "true" }; break;
                case "DropdownField": element = new DropdownField { label = (string)node.Attribute("label") ?? "" }; break;
                case "Toggle": element = new Toggle { text = (string)node.Attribute("text") ?? "", value = (string)node.Attribute("value") == "true" }; break;
                case "Slider": element = new Slider { lowValue = Number(node,"low-value",0), highValue = Number(node,"high-value",100), value = Number(node,"value",0) }; break;
                case "ProgressBar": element = new ProgressBar { lowValue = Number(node,"low-value",0), highValue = Number(node,"high-value",100), title = (string)node.Attribute("title") ?? "" }; break;
                default: throw new InvalidOperationException("Unsupported owned UXML fixture element: " + node.Name.LocalName);
            }
            element.name = (string)node.Attribute("name") ?? ""; element.tooltip = (string)node.Attribute("tooltip") ?? "";
            element.focusable = (string)node.Attribute("focusable") == "true" || element.focusable;
            foreach (string token in ((string)node.Attribute("class") ?? "").Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries)) element.AddToClassList(token);
            if (element is TextField field && int.TryParse((string)node.Attribute("max-length"),out int length)) field.maxLength = length;
            foreach (var child in node.Elements()) element.Add(Create(child));
            return element;
        }
        private static float Number(XElement node,string attribute,float fallback)
            => float.TryParse((string)node.Attribute(attribute),NumberStyles.Float,CultureInfo.InvariantCulture,out float value)?value:fallback;
    }
}

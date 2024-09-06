---
title: "Accurate and Fast Prediction of Intrinsically Disordered Protein by Multiple Protein Language Models and Ensemble Learning"
authors:
- Shijie Xu
- Akira Onoda*
# author_notes:
# - "Equal contribution"
# - "Equal contribution"
date: "2023-10-26T00:00:00Z"
doi: "10.1021/acs.jcim.3c01202"

# Schedule page publish date (NOT publication's date).
publishDate: "2023-10-26T00:00:00Z"

# Publication type.
# Accepts a single type but formatted as a YAML list (for Hugo requirements).
# Enter a publication type from the CSL standard.
publication_types: ["article-journal"]

# Publication name and optional abbreviated publication name.
publication: "Journal of Chemical Information and Modeling"
publication_short: "J. Chem. Inf. Model"

abstract: Intrinsically disordered proteins (IDPs) play a vital role in various biological processes and have attracted increasing attention in the past few decades. Predicting IDPs from the primary structures of proteins offers a rapid and facile means of protein analysis without necessitating crystal structures. In particular, machine learning methods have demonstrated their potential in this field. Recently, protein language models (PLMs) are emerging as a promising approach to extracting essential information from protein sequences and have been employed in protein modeling to utilize their advantages of precision and efficiency. In this article, we developed a novel IDP prediction method named IDP-ELM to predict the intrinsically disordered regions (IDRs) as well as their functions including disordered flexible linkers and disordered protein binding. This method utilizes high-dimensional representations extracted from several state-of-the-art PLMs and predicts IDRs by ensemble learning based on bidirectional recurrent neural networks. The performance of the method was evaluated on two independent test data sets from CAID (critical assessment of protein intrinsic disorder prediction) and CAID2, indicating notable improvements in terms of area under the receiver operating characteristic (AUC), Matthew’s correlation coefficient (MCC), and F1 score. Moreover, IDP-ELM requires solely protein sequences as inputs and does not entail a time-consuming process of protein profile generation, which is a prerequisite for most existing state-of-the-art methods, enabling an accurate, fast, and convenient tool for proteome-level analysis. The corresponding reproducible source code and model weights are available at https://github.com/xu-shi-jie/idp-elm.

# Summary. An optional shortened abstract.
# summary: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis posuere tellus ac convallis placerat. Proin tincidunt magna sed ex sollicitudin condimentum.

# Summarize in 50 words
summary: Intrinsically disordered proteins (IDPs) play a vital role in various biological processes and have attracted increasing attention in the past few decades. They are challenging to predict due to their high flexibility. In this article, Xu and Onoda developed a novel MSA-free algorithm based on the protein language models, to predict IDPs and their functions, which is accurate, fast, and convenient to use.

tags:
- Source Themes
featured: true

# links:
# - name: ""
#   url: ""
url_pdf: https://pubs.acs.org/doi/epdf/10.1021/acs.jcim.3c01202
url_code: 'https://github.com/xu-shi-jie/idp-elm'
url_dataset: ''
url_poster: ''
url_project: ''
url_slides: ''
url_source: ''
url_video: ''

# Featured image
# To use, add an image named `featured.jpg/png` to your page's folder. 
image:
  caption: 'Image credit: [**Onoda Lab**](fix_0927.png)'
  focal_point: ""
  preview_only: false

# Associated Projects (optional).
#   Associate this publication with one or more of your projects.
#   Simply enter your project's folder or file name without extension.
#   E.g. `internal-project` references `content/project/internal-project/index.md`.
#   Otherwise, set `projects: []`.
projects: []

# Slides (optional).
#   Associate this publication with Markdown slides.
#   Simply enter your slide deck's filename without extension.
#   E.g. `slides: "example"` references `content/slides/example/index.md`.
#   Otherwise, set `slides: "`.
# slides: example

commentable: true
---

<!-- {{% callout note %}}
Click the *Cite* button above to demo the feature to enable visitors to import publication metadata into their reference management software.
{{% /callout %}} -->

<!-- {{% callout note %}}
Create your slides in Markdown - click the *Slides* button to check out the example.
{{% /callout %}} -->

<!-- Add the publication's **full text** or **supplementary notes** here. You can use rich formatting such as including [code, math, and images](https://docs.hugoblox.com/content/writing-markdown-latex/). -->

```diff
  Unchanged Line
- Due to the limitation of computational resources, we are currently unable to provide the web server for IDP-ELM. If you want to utilize the IDP prediction for your research, please contact us via email (shijie.xu@ees.hokudai.ac.jp). We are glad to provide the prediction results for you as soon as possible, including the predicted IDRs and their functions.
+ Our publicly available are now published! [https://onodalab.ees.hokudai.ac.jp/idp-elm](https://onodalab.ees.hokudai.ac.jp/idp-elm)
```

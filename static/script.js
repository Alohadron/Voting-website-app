const voteButtons = document.querySelectorAll(".vote-button");
const modal = document.querySelector(".modal");
const modalImageContainer = document.querySelector(".modal-image-container");
const confirmButton = document.querySelector(".modal-button.confirm");
const cancelButton = document.querySelector(".modal-button.cancel");

let currentPath = window.location.pathname;
let redirect_path;

if (currentPath === "/first_vote") {
  redirect_path = "second_vote";
} else if (currentPath === "/second_vote") {
  redirect_path = "third_vote";
} else if (currentPath === "/third_vote") {
  redirect_path = "final_vote";
} else if (currentPath === "/final_vote") {
  redirect_path = "results";
} else {
  console.log("javascript redirect_path Error");
}

// Function to fetch sub-images from the server based on candidate ID
async function fetchImages(candidateId) {
  try {
    const response = await fetch(`/api/candidate_images/${candidateId}`);

    if (!response.ok) {
      throw new Error(`Error: ${response.status} - ${response.statusText}`);
    }

    const data = await response.json();

    // Check if data contains images and return them
    if (data.images && data.images.length > 0) {
      return data.images; // Return the list of sub-images for the candidate
    } else {
      console.error("No images found for the candidate.");
      return [];
    }
  } catch (error) {
    console.error("Failed to fetch images:", error);
    return [];
  }
}

let likedImages = [];

// Open modal and load sub-images
voteButtons.forEach((button) => {
  button.addEventListener("click", async (event) => {
    const candidateId = button.getAttribute("data-candidate-id");
    const candidateName =
      button.parentElement.querySelector(".candidate-name").innerText;
    const images = await fetchImages(candidateId); // Fetch sub-images for the candidate

    // Clear previous images in the modal
    modalImageContainer.innerHTML = "";

    // Display candidate name if on final_vote page
    if (currentPath === "/final_vote") {
      document.querySelector(".modal .candidate-name").innerText =
        candidateName;
    }

    images.forEach((imageUrl, index) => {
      const imgElement = document.createElement("img");
      imgElement.src = `/${imageUrl}`;
      imgElement.alt = `Image for candidate ${candidateId}`;
      imgElement.classList.add("modal-image");
      imgElement.setAttribute("data-candidate-id", candidateId); // Set data-candidate-id

      const imageItem = document.createElement("div");
      imageItem.classList.add("modal-image-item");
      imageItem.appendChild(imgElement);

      // Conditionally display the heart button (only if not on final_vote page)
      if (currentPath !== "/final_vote") {
        const heartButton = document.createElement("button");
        heartButton.classList.add("like-button");
        heartButton.innerHTML = `
          <svg class="heart" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
          </svg>
        `;

        // Create a unique identifier for the image
        const imageId = `${candidateId}_${index + 1}`;

        // Check if this image is liked and update the heart button accordingly
        if (likedImages.includes(imageId)) {
          heartButton.classList.add("liked"); // Mark as liked if found
        } else {
          heartButton.classList.remove("liked"); // Ensure it's not marked if not liked
        }

        // Add click event listener for the heart button
        heartButton.addEventListener("click", async () => {
          heartButton.classList.toggle("liked"); // Toggle the 'liked' class

          // Track liked or unliked state for the image
          if (heartButton.classList.contains("liked")) {
            likedImages.push(imageId); // Add image to liked images
            await sendLikeUpdate(candidateId, index + 1, true); // Send like count
          } else {
            likedImages = likedImages.filter((id) => id !== imageId); // Remove image if unliked
            await sendLikeUpdate(candidateId, index + 1, false); // Send unlike count
          }

          // Debugging log
          console.log("Current likedImages:", likedImages);
        });

        imageItem.appendChild(heartButton); // Append the heart button only if not on final_vote page
      }

      modalImageContainer.appendChild(imageItem); // Always append images to the modal
    });

    modal.classList.add("open"); // Show the modal
  });
});

// Close modal on cancel
if (currentPath != "/main") {
  cancelButton.addEventListener("click", () => {
    modal.classList.remove("open");
  });
}

// Handle the confirm button click
if (currentPath != "/main") {
  confirmButton.addEventListener("click", async () => {
    const candidateId = modalImageContainer
      .querySelector("img")
      .getAttribute("data-candidate-id");

    // Prepare data to send
    const formData = new FormData();
    formData.append("image_id", candidateId);
    formData.append("redirect_path", redirect_path); // Redirect to the correct page after voting

    // Send the POST request
    const response = await fetch("/vote", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      window.location.href = redirect_path; // Redirect to the next voting page
    } else {
      console.error("Failed to cast vote");
    }
  });
}

const likeButtons = document.querySelectorAll(".like-button");

likeButtons.forEach((button) => {
  let isLiked = false; // Track if the heart is liked

  button.addEventListener("click", () => {
    isLiked = !isLiked; // Toggle the liked state
  });
});

async function sendLikeUpdate(candidateId, index, isLiked) {
  const formData = new FormData();
  formData.append("candidate_id", candidateId);
  formData.append("index", index);
  formData.append("isLiked", isLiked); // Boolean for like or unlike

  await fetch("/update_like", {
    method: "POST",
    body: formData,
  });
}
